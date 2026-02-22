package com.athena.notificationservice.repository;

import com.athena.notificationservice.model.NotificationLog;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface NotificationLogRepository extends JpaRepository<NotificationLog, Long> {
    List<NotificationLog> findByServiceName(String serviceName);
    List<NotificationLog> findByRecipient(String recipient);
    List<NotificationLog> findByType(String type);
}
