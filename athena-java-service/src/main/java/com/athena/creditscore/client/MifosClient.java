package com.athena.creditscore.client;

import com.athena.creditscore.dto.MifosTransactionResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * OpenFeign client for Mifos X / Apache Fineract core banking system.
 * Adapted from athena-device-finance customer-service client patterns.
 */
@FeignClient(name = "mifos-client", url = "${mifos.base-url}")
public interface MifosClient {

    /**
     * Get all transactions for a savings account.
     * @param accountId Mifos savings account ID
     * @param limit     Max transactions to retrieve
     */
    @GetMapping("/savingsaccounts/{accountId}/transactions")
    List<MifosTransactionResponse> getSavingsTransactions(
            @PathVariable("accountId") String accountId,
            @RequestParam(value = "limit", defaultValue = "500") int limit,
            @RequestHeader("Authorization") String basicAuth
    );

    /**
     * Get client details by Mifos client ID.
     */
    @GetMapping("/clients/{clientId}")
    Object getClientDetails(
            @PathVariable("clientId") String clientId,
            @RequestHeader("Authorization") String basicAuth
    );

    /**
     * Get loan accounts for a client.
     */
    @GetMapping("/clients/{clientId}/accounts")
    Object getClientAccounts(
            @PathVariable("clientId") String clientId,
            @RequestHeader("Authorization") String basicAuth
    );
}
