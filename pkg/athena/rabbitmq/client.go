package rabbitmq

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/rs/zerolog/log"
)

const (
	ExchangeName     = "athena.exchange"
	NotificationQueue = "athena.notification.queue"
	ScoringQueue     = "athena.scoring.queue"
	DisputeQueue     = "athena.dispute.queue"

	NotificationKey = "athena.notification.routingKey"
	ScoringKey      = "athena.scoring.routingKey"
	DisputeKey      = "athena.dispute.routingKey"
)

type Client struct {
	conn    *amqp.Connection
	ch      *amqp.Channel
	mu      sync.Mutex
	url     string
}

func NewClient(url string) (*Client, error) {
	c := &Client{url: url}
	if err := c.connect(); err != nil {
		return nil, err
	}
	return c, nil
}

func (c *Client) connect() error {
	conn, err := amqp.Dial(c.url)
	if err != nil {
		return fmt.Errorf("rabbitmq: dial: %w", err)
	}
	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
		return fmt.Errorf("rabbitmq: channel: %w", err)
	}

	// Declare exchange
	if err := ch.ExchangeDeclare(ExchangeName, "direct", true, false, false, false, nil); err != nil {
		ch.Close()
		conn.Close()
		return fmt.Errorf("rabbitmq: exchange declare: %w", err)
	}

	// Declare and bind queues
	queues := []struct {
		name string
		key  string
	}{
		{NotificationQueue, NotificationKey},
		{ScoringQueue, ScoringKey},
		{DisputeQueue, DisputeKey},
	}
	for _, q := range queues {
		if _, err := ch.QueueDeclare(q.name, true, false, false, false, nil); err != nil {
			ch.Close()
			conn.Close()
			return fmt.Errorf("rabbitmq: queue declare %s: %w", q.name, err)
		}
		if err := ch.QueueBind(q.name, q.key, ExchangeName, false, nil); err != nil {
			ch.Close()
			conn.Close()
			return fmt.Errorf("rabbitmq: queue bind %s: %w", q.name, err)
		}
	}

	c.conn = conn
	c.ch = ch
	log.Info().Msg("rabbitmq: connected and topology declared")
	return nil
}

func (c *Client) Publish(routingKey string, msg interface{}) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	body, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("rabbitmq: marshal: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	return c.ch.PublishWithContext(ctx, ExchangeName, routingKey, false, false, amqp.Publishing{
		ContentType:  "application/json",
		Body:         body,
		DeliveryMode: amqp.Persistent,
	})
}

func (c *Client) Consume(queueName string) (<-chan amqp.Delivery, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	return c.ch.Consume(queueName, "", false, false, false, false, nil)
}

func (c *Client) Close() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.ch != nil {
		c.ch.Close()
	}
	if c.conn != nil {
		c.conn.Close()
	}
}
