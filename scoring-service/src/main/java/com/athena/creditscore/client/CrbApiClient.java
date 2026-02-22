package com.athena.creditscore.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;
import java.util.UUID;

import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * WebClient-based CRB integration client with retry (exponential backoff).
 * Supports TransUnion Kenya and Metropol via configuration.
 */
@Component
@Slf4j
public class CrbApiClient {

    private final WebClient webClient;

    @Value("${transunion.api-key:}")
    private String transunionApiKey;
    @Value("${transunion.url:}")
    private String transunionUrl;

    @Value("${metropol.api-key:}")
    private String metropolApiKey;
    @Value("${metropol.url:}")
    private String metropolUrl;

    public CrbApiClient(WebClient.Builder builder) {
        this.webClient = builder.build();
    }

    @Retryable(maxAttempts = 3, backoff = @Backoff(delay = 1000, multiplier = 2))
    public Mono<Map> fetchTransUnionReport(String nationalId) {
        log.info("Fetching TransUnion report for: {}", nationalId);
        return webClient.post()
                .uri(transunionUrl)
                .header("Authorization", "Bearer " + transunionApiKey)
                .header("Content-Type", "application/json")
                .bodyValue(Map.of(
                        "nationalId", nationalId,
                        "requestId", UUID.randomUUID().toString()
                ))
                .retrieve()
                .onStatus(HttpStatusCode::isError, resp ->
                        resp.bodyToMono(String.class)
                                .flatMap(body -> Mono.error(new RuntimeException("TransUnion error: " + body)))
                )
                .bodyToMono(Map.class)
                .doOnSuccess(r -> log.info("TransUnion report received for {}", nationalId))
                .doOnError(e -> log.error("TransUnion fetch failed for {}: {}", nationalId, e.getMessage()));
    }

    @Retryable(maxAttempts = 3, backoff = @Backoff(delay = 1000, multiplier = 2))
    public Mono<Map> fetchMetropolReport(String nationalId) {
        log.info("Fetching Metropol report for: {}", nationalId);
        return webClient.post()
                .uri(metropolUrl)
                .header("X-Api-Key", metropolApiKey)
                .header("Content-Type", "application/json")
                .bodyValue(Map.of("nationalId", nationalId))
                .retrieve()
                .onStatus(HttpStatusCode::isError, resp ->
                        resp.bodyToMono(String.class)
                                .flatMap(body -> Mono.error(new RuntimeException("Metropol error: " + body)))
                )
                .bodyToMono(Map.class)
                .doOnSuccess(r -> log.info("Metropol report received for {}", nationalId))
                .doOnError(e -> log.error("Metropol fetch failed for {}: {}", nationalId, e.getMessage()));
    }
}
