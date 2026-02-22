package com.athena.creditscore.dto;

import lombok.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MifosTransactionResponse {
    private Long id;
    private String date;
    private Double amount;
    private String type;             // deposit, withdrawal, transfer
    private String submittedByUsername;
    private String currency;
    private Double runningBalance;
}
