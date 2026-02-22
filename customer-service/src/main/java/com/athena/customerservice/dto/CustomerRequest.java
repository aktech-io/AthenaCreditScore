package com.athena.customerservice.dto;

import lombok.Data;
import java.time.LocalDate;

@Data
public class CustomerRequest {
    private String firstName;
    private String lastName;
    private String mobileNumber;
    private String email;
    private String nationalId;
    private LocalDate dateOfBirth;
    private String gender; // MALE, FEMALE
    private String county;
    private String region;
    private String bankName;
    private String accountNumber;
    private String registrationChannel; // WEB_APP, MOBILE_APP, ADMIN_PORTAL, PARTNER_API
}
