package com.athena.customerservice.dto;

import lombok.Data;
import java.util.UUID;

@Data
public class MediaResponse {
    private UUID id;
    private String mediaType;
    private String originalFilename;
    private String contentType;
    private Long fileSize;
    private String serviceName;
    private String channel;
}
