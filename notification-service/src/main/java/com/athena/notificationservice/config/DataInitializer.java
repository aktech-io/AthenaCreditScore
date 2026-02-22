package com.athena.notificationservice.config;

import com.athena.notificationservice.model.NotificationConfig;
import com.athena.notificationservice.repository.NotificationConfigRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class DataInitializer implements CommandLineRunner {

    private final NotificationConfigRepository configRepository;

    @Override
    public void run(String... args) {
        if (configRepository.findByType("EMAIL").isEmpty()) {
            log.info("Seeding default EMAIL notification config (disabled — configure via API)");
            configRepository.save(NotificationConfig.builder()
                    .type("EMAIL")
                    .provider("SMTP")
                    .host("smtp.gmail.com")
                    .port(587)
                    .username("")
                    .password("")
                    .fromAddress("noreply@athena.co.ke")
                    .enabled(false)
                    .build());
        }

        if (configRepository.findByType("SMS").isEmpty()) {
            log.info("Seeding default SMS notification config (disabled — configure via API)");
            configRepository.save(NotificationConfig.builder()
                    .type("SMS")
                    .provider("AFRICAS_TALKING")
                    .senderId("ATHENA")
                    .apiKey("")
                    .apiSecret("")
                    .enabled(false)
                    .build());
        }
    }
}
