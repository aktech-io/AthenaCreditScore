package com.athena.notificationservice.repository;

import com.athena.notificationservice.model.NotificationConfig;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface NotificationConfigRepository extends JpaRepository<NotificationConfig, Long> {
    Optional<NotificationConfig> findByType(String type);
}
