package com.athena.mediaservice.controller;

import com.athena.mediaservice.config.JwtUtil;
import com.athena.mediaservice.model.Media;
import com.athena.mediaservice.service.MediaService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/media")
@RequiredArgsConstructor
@Tag(name = "Media", description = "Customer document upload and download")
public class MediaController {

    private final MediaService mediaService;
    private final JwtUtil jwtUtil;

    private String extractUsername(String authHeader) {
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return jwtUtil.extractUsername(authHeader.substring(7));
        }
        return "system";
    }

    @PostMapping("/upload/{customerId}")
    @Operation(summary = "Upload a document for a customer")
    public ResponseEntity<Media> uploadForCustomer(
            @PathVariable Long customerId,
            @RequestParam("file") MultipartFile file,
            @RequestParam("mediaType") Media.MediaType mediaType,
            @RequestParam(value = "category", defaultValue = "CUSTOMER_DOCUMENT") Media.MediaCategory category,
            @RequestParam(value = "description", required = false) String description,
            @RequestHeader(value = "Authorization", required = false) String authHeader) {
        String uploadedBy = extractUsername(authHeader);
        Media media = mediaService.uploadMedia(customerId, file, mediaType, category, description, uploadedBy);
        return ResponseEntity.ok(media);
    }

    @PostMapping("/upload")
    @Operation(summary = "Upload media with category-based organisation")
    public ResponseEntity<Media> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam("category") Media.MediaCategory category,
            @RequestParam("mediaType") Media.MediaType mediaType,
            @RequestParam(value = "referenceId", required = false) UUID referenceId,
            @RequestParam(value = "description", required = false) String description,
            @RequestParam(value = "tags", required = false) String tags,
            @RequestParam(value = "isPublic", defaultValue = "false") Boolean isPublic,
            @RequestParam(value = "serviceName", required = false) String serviceName,
            @RequestParam(value = "channel", required = false) String channel,
            @RequestHeader(value = "Authorization", required = false) String authHeader) {
        String uploadedBy = extractUsername(authHeader);
        Media media = mediaService.uploadMedia(file, category, mediaType, referenceId,
                description, tags, isPublic, uploadedBy, serviceName, channel);
        return ResponseEntity.ok(media);
    }

    @GetMapping("/customer/{customerId}")
    @Operation(summary = "List all media for a customer")
    public ResponseEntity<List<Media>> getCustomerMedia(@PathVariable Long customerId) {
        return ResponseEntity.ok(mediaService.getMediaByCustomer(customerId));
    }

    @GetMapping("/download/{mediaId}")
    @Operation(summary = "Download a media file by ID")
    public ResponseEntity<Resource> downloadMedia(@PathVariable UUID mediaId) {
        Media metadata = mediaService.getMediaMetadata(mediaId);
        Resource resource = mediaService.downloadMedia(mediaId);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(metadata.getContentType()))
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + metadata.getOriginalFilename() + "\"")
                .body(resource);
    }

    @GetMapping("/metadata/{mediaId}")
    @Operation(summary = "Get metadata for a specific media file")
    public ResponseEntity<Media> getMetadata(@PathVariable UUID mediaId) {
        return ResponseEntity.ok(mediaService.getMediaMetadata(mediaId));
    }

    @GetMapping("/reference/{referenceId}")
    @Operation(summary = "Get all media for a reference entity")
    public ResponseEntity<List<Media>> getByReference(@PathVariable UUID referenceId) {
        return ResponseEntity.ok(mediaService.findByReferenceId(referenceId));
    }

    @GetMapping("/category/{category}")
    @Operation(summary = "Get all media for a category")
    public ResponseEntity<List<Media>> getByCategory(@PathVariable Media.MediaCategory category) {
        return ResponseEntity.ok(mediaService.findByCategory(category));
    }

    @GetMapping
    @Operation(summary = "Search/list media by category, status, or tag")
    public ResponseEntity<List<Media>> search(
            @RequestParam(value = "category", required = false) Media.MediaCategory category,
            @RequestParam(value = "status", required = false) Media.MediaStatus status,
            @RequestParam(value = "tag", required = false) String tag) {
        if (tag != null && !tag.isEmpty()) {
            return ResponseEntity.ok(mediaService.findByTag(tag));
        }
        return ResponseEntity.ok(mediaService.searchMedia(category, status));
    }

    @PatchMapping("/{mediaId}")
    @Operation(summary = "Update media description, tags, or status")
    public ResponseEntity<Media> updateMetadata(
            @PathVariable UUID mediaId,
            @RequestParam(value = "description", required = false) String description,
            @RequestParam(value = "tags", required = false) String tags,
            @RequestParam(value = "status", required = false) Media.MediaStatus status) {
        return ResponseEntity.ok(mediaService.updateMetadata(mediaId, description, tags, status));
    }

    @DeleteMapping("/{mediaId}")
    @Operation(summary = "Delete a media file")
    public ResponseEntity<Void> deleteMedia(@PathVariable UUID mediaId) {
        mediaService.deleteMedia(mediaId);
        return ResponseEntity.noContent().build();
    }
}
