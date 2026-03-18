package cache

import (
	"fmt"
	"time"

	gocache "github.com/patrickmn/go-cache"
)

type CreditCache struct {
	c *gocache.Cache
}

func New() *CreditCache {
	return &CreditCache{
		c: gocache.New(1*time.Hour, 10*time.Minute),
	}
}

func (cc *CreditCache) GetScore(customerID int64) (map[string]interface{}, bool) {
	key := fmt.Sprintf("score:%d", customerID)
	val, found := cc.c.Get(key)
	if !found {
		return nil, false
	}
	return val.(map[string]interface{}), true
}

func (cc *CreditCache) SetScore(customerID int64, data map[string]interface{}) {
	key := fmt.Sprintf("score:%d", customerID)
	cc.c.Set(key, data, gocache.DefaultExpiration)
}

func (cc *CreditCache) GetReport(customerID int64) (map[string]interface{}, bool) {
	key := fmt.Sprintf("report:%d", customerID)
	val, found := cc.c.Get(key)
	if !found {
		return nil, false
	}
	return val.(map[string]interface{}), true
}

func (cc *CreditCache) SetReport(customerID int64, data map[string]interface{}) {
	key := fmt.Sprintf("report:%d", customerID)
	cc.c.Set(key, data, gocache.DefaultExpiration)
}
