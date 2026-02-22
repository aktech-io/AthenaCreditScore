package com.athena.mediaservice.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Athena Media Service API")
                        .version("1.0")
                        .description("Media storage and retrieval service for Athena Credit Score Platform")
                        .contact(new Contact()
                                .name("Athena Team")
                                .email("support@athena.co.ke")));
    }
}
