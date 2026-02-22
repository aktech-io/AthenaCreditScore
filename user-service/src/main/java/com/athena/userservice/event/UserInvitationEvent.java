package com.athena.userservice.event;

import lombok.*;

import java.io.Serializable;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserInvitationEvent implements Serializable {
    private String email;
    private String token;
}
