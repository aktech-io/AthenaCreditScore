package com.athena.creditscore.client;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.*;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;

@DisplayName("CrbApiClient Tests")
class CrbApiClientTest {

    private static MockWebServer mockWebServer;
    private CrbApiClient client;

    @BeforeAll
    static void startServer() throws IOException {
        mockWebServer = new MockWebServer();
        mockWebServer.start();
    }

    @AfterAll
    static void stopServer() throws IOException {
        mockWebServer.shutdown();
    }

    @BeforeEach
    void setUp() {
        String baseUrl = mockWebServer.url("/").toString().replaceAll("/$", "");
        client = new CrbApiClient(WebClient.builder());

        // Inject test URLs
        org.springframework.test.util.ReflectionTestUtils.setField(client, "transunionUrl", baseUrl + "/transunion");
        org.springframework.test.util.ReflectionTestUtils.setField(client, "transunionApiKey", "test-key");
        org.springframework.test.util.ReflectionTestUtils.setField(client, "metropolUrl", baseUrl + "/metropol");
        org.springframework.test.util.ReflectionTestUtils.setField(client, "metropolApiKey", "test-key");
    }

    @Test
    @DisplayName("fetchTransUnionReport — 200 OK → returns parsed Map")
    void shouldReturnParsedReportOnSuccess() {
        mockWebServer.enqueue(new MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody("{\"bureauScore\": 650, \"bureauName\": \"TransUnion\"}"));

        Map result = client.fetchTransUnionReport("27005899").block();

        assertThat(result).isNotNull();
        assertThat(result.get("bureauScore")).isEqualTo(650);
        assertThat(result.get("bureauName")).isEqualTo("TransUnion");
    }

    @Test
    @DisplayName("fetchMetropolReport — 200 OK → returns parsed Map")
    void shouldReturnMetropolReport() {
        mockWebServer.enqueue(new MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody("{\"bureauScore\": 580, \"bureauName\": \"Metropol\"}"));

        Map result = client.fetchMetropolReport("27005899").block();

        assertThat(result).isNotNull();
        assertThat(result.get("bureauName")).isEqualTo("Metropol");
    }

    @Test
    @DisplayName("fetchTransUnionReport — 500 server error → throws RuntimeException")
    void shouldThrowOnServerError() {
        mockWebServer.enqueue(new MockResponse()
                .setResponseCode(500)
                .setBody("Internal Server Error"));

        assertThatThrownBy(() -> client.fetchTransUnionReport("27005899").block())
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("TransUnion error");
    }

    @Test
    @DisplayName("fetchTransUnionReport — sends correct nationalId in body")
    void shouldSendNationalIdInRequest() throws InterruptedException {
        mockWebServer.enqueue(new MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody("{\"bureauScore\": 700}"));

        client.fetchTransUnionReport("TEST-NATIONAL-ID").block();

        var recordedRequest = mockWebServer.takeRequest();
        assertThat(recordedRequest.getBody().readUtf8()).contains("TEST-NATIONAL-ID");
        assertThat(recordedRequest.getHeader("Authorization")).startsWith("Bearer ");
    }
}
