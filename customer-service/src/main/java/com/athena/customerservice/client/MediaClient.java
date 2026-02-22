package com.athena.customerservice.client;

import com.athena.customerservice.dto.MediaResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

import java.util.UUID;

@FeignClient(name = "media-service", url = "${services.media-service.url:http://media-service:8083}")
public interface MediaClient {

    @GetMapping("/api/v1/media/{id}")
    MediaResponse getMediaMetadata(@PathVariable UUID id);
}
