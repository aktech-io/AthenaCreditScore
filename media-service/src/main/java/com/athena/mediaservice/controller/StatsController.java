package com.athena.mediaservice.controller;

import com.athena.mediaservice.model.Media;
import com.athena.mediaservice.service.MediaService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/media/stats")
@RequiredArgsConstructor
@Tag(name = "Media Stats", description = "Storage statistics and paginated media listing")
public class StatsController {

    private final MediaService mediaService;

    @GetMapping
    @Operation(summary = "Get storage and document statistics")
    public ResponseEntity<Map<String, Object>> getStats() {
        return ResponseEntity.ok(mediaService.getStats());
    }

    @GetMapping("/all")
    @Operation(summary = "List all media files (paginated)")
    public ResponseEntity<Page<Media>> getAllMedia(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(mediaService.getAllMedia(PageRequest.of(page, size)));
    }
}
