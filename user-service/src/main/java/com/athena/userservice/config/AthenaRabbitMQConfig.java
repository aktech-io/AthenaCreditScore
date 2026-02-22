package com.athena.userservice.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class AthenaRabbitMQConfig {

    public static final String NOTIFICATION_QUEUE   = "athena.notification.queue";
    public static final String SCORING_EXCHANGE     = "athena.exchange";
    public static final String NOTIFICATION_KEY     = "athena.notification.routingKey";

    @Bean public DirectExchange athenaExchange() { return new DirectExchange(SCORING_EXCHANGE); }
    @Bean public Queue notificationQueue()       { return new Queue(NOTIFICATION_QUEUE, true); }

    @Bean
    public Binding notificationBinding(Queue notificationQueue, DirectExchange athenaExchange) {
        return BindingBuilder.bind(notificationQueue).to(athenaExchange).with(NOTIFICATION_KEY);
    }

    @Bean
    public MessageConverter messageConverter() {
        return new Jackson2JsonMessageConverter();
    }
}
