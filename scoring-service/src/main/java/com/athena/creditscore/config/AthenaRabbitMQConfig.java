package com.athena.creditscore.config;

// Adapted from athena-device-finance user-service RabbitMQConfig.java
import org.springframework.amqp.core.*;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class AthenaRabbitMQConfig {

    // Scoring events queue
    public static final String SCORING_QUEUE    = "athena.scoring.queue";
    public static final String SCORING_EXCHANGE = "athena.exchange";
    public static final String SCORING_KEY      = "athena.scoring.routingKey";

    // Notification queue (reused notification-service pattern)
    public static final String NOTIFICATION_QUEUE    = "athena.notification.queue";
    public static final String NOTIFICATION_KEY      = "athena.notification.routingKey";

    // Dispute queue
    public static final String DISPUTE_QUEUE = "athena.dispute.queue";
    public static final String DISPUTE_KEY   = "athena.dispute.routingKey";

    @Bean
    public DirectExchange athenaExchange() {
        return new DirectExchange(SCORING_EXCHANGE);
    }

    @Bean public Queue scoringQueue()      { return new Queue(SCORING_QUEUE, true); }
    @Bean public Queue notificationQueue() { return new Queue(NOTIFICATION_QUEUE, true); }
    @Bean public Queue disputeQueue()      { return new Queue(DISPUTE_QUEUE, true); }

    @Bean public Binding scoringBinding(Queue scoringQueue, DirectExchange athenaExchange) {
        return BindingBuilder.bind(scoringQueue).to(athenaExchange).with(SCORING_KEY);
    }
    @Bean public Binding notificationBinding(Queue notificationQueue, DirectExchange athenaExchange) {
        return BindingBuilder.bind(notificationQueue).to(athenaExchange).with(NOTIFICATION_KEY);
    }
    @Bean public Binding disputeBinding(Queue disputeQueue, DirectExchange athenaExchange) {
        return BindingBuilder.bind(disputeQueue).to(athenaExchange).with(DISPUTE_KEY);
    }

    @Bean
    public MessageConverter messageConverter() {
        return new Jackson2JsonMessageConverter();
    }
}
