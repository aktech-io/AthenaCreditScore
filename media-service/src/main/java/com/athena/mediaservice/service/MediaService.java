package com.athena.mediaservice.service;

import com.athena.mediaservice.model.Media;
import com.athena.mediaservice.repository.MediaRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.MalformedURLException;
import java.nio.file.*;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class MediaService {

    private final MediaRepository mediaRepository;

    @Value("${storage.location:/app/storage}")
    private String storageLocation;

    private Path rootLocation;

    @PostConstruct
    public void init() {
        this.rootLocation = Paths.get(storageLocation);
        try {
            Files.createDirectories(rootLocation);
            log.info("Storage initialized at: {}", rootLocation.toAbsolutePath());
        } catch (IOException e) {
            throw new RuntimeException("Could not initialize storage", e);
        }
    }

    // Customer-scoped upload (backwards-compatible)
    public Media uploadMedia(Long customerId, MultipartFile file,
            Media.MediaType mediaType, Media.MediaCategory category,
            String description, String uploadedBy) {
        return doUpload(file, category, mediaType, null, description, null, false,
                uploadedBy, null, null, customerId);
    }

    // General-purpose upload (with referenceId, tags, isPublic, serviceName, channel)
    public Media uploadMedia(MultipartFile file, Media.MediaCategory category,
            Media.MediaType mediaType, UUID referenceId, String description,
            String tags, Boolean isPublic, String uploadedBy,
            String serviceName, String channel) {
        return doUpload(file, category, mediaType, referenceId, description,
                tags, isPublic, uploadedBy, serviceName, channel, null);
    }

    private Media doUpload(MultipartFile file, Media.MediaCategory category,
            Media.MediaType mediaType, UUID referenceId, String description,
            String tags, Boolean isPublic, String uploadedBy,
            String serviceName, String channel, Long customerId) {
        if (file.isEmpty()) throw new RuntimeException("Cannot upload empty file");

        String originalFilename = file.getOriginalFilename();
        String storedFilename = UUID.randomUUID() + getExtension(originalFilename);

        try {
            Path dest = rootLocation.resolve(Paths.get(storedFilename)).normalize().toAbsolutePath();
            if (!dest.getParent().equals(rootLocation.toAbsolutePath())) {
                throw new RuntimeException("Cannot store file outside storage directory");
            }
            Files.copy(file.getInputStream(), dest, StandardCopyOption.REPLACE_EXISTING);

            Media media = Media.builder()
                    .referenceId(referenceId)
                    .customerId(customerId)
                    .category(category)
                    .mediaType(mediaType)
                    .originalFilename(originalFilename)
                    .storedFilename(storedFilename)
                    .contentType(file.getContentType())
                    .fileSize(file.getSize())
                    .description(description)
                    .tags(tags)
                    .isPublic(isPublic != null ? isPublic : false)
                    .uploadedBy(uploadedBy)
                    .serviceName(serviceName)
                    .channel(channel)
                    .status(Media.MediaStatus.ACTIVE)
                    .build();

            Media saved = mediaRepository.save(media);
            log.info("Media uploaded: {} category: {} customer: {} reference: {}",
                    saved.getId(), category, customerId, referenceId);
            return saved;
        } catch (IOException e) {
            throw new RuntimeException("Failed to store file: " + originalFilename, e);
        }
    }

    @Cacheable(value = "mediaContent", key = "#mediaId")
    public Resource downloadMedia(UUID mediaId) {
        Media media = mediaRepository.findById(mediaId)
                .orElseThrow(() -> new RuntimeException("Media not found: " + mediaId));
        try {
            Path file = rootLocation.resolve(media.getStoredFilename());
            Resource resource = new UrlResource(file.toUri());
            if (resource.exists() && resource.isReadable()) return resource;
            throw new RuntimeException("Could not read file: " + media.getOriginalFilename());
        } catch (MalformedURLException e) {
            throw new RuntimeException("Could not read file", e);
        }
    }

    @Cacheable(value = "mediaMetadata", key = "#mediaId")
    public Media getMediaMetadata(UUID mediaId) {
        return mediaRepository.findById(mediaId)
                .orElseThrow(() -> new RuntimeException("Media not found: " + mediaId));
    }

    public List<Media> getMediaByCustomer(Long customerId) {
        return mediaRepository.findByCustomerId(customerId);
    }

    public List<Media> findByCategory(Media.MediaCategory category) {
        return mediaRepository.findByCategory(category);
    }

    public List<Media> findByReferenceId(UUID referenceId) {
        return mediaRepository.findByReferenceId(referenceId);
    }

    public List<Media> findByTag(String tag) {
        return mediaRepository.findByTagsContaining(tag);
    }

    public List<Media> searchMedia(Media.MediaCategory category, Media.MediaStatus status) {
        if (category == null && status == null) {
            return mediaRepository.findAll();
        }
        return mediaRepository.searchMedia(category, status, null, null);
    }

    public Media updateMetadata(UUID mediaId, String description, String tags, Media.MediaStatus status) {
        Media media = mediaRepository.findById(mediaId)
                .orElseThrow(() -> new RuntimeException("Media not found: " + mediaId));
        if (description != null) media.setDescription(description);
        if (tags != null) media.setTags(tags);
        if (status != null) media.setStatus(status);
        Media updated = mediaRepository.save(media);
        log.info("Media metadata updated: {}", mediaId);
        return updated;
    }

    public Page<Media> getAllMedia(Pageable pageable) {
        return mediaRepository.findAll(pageable);
    }

    public Map<String, Object> getStats() {
        java.io.File storageDir = new java.io.File(storageLocation);
        long totalSpace = storageDir.getTotalSpace();
        long freeSpace = storageDir.getFreeSpace();
        long usedSpace = mediaRepository.findAll().stream()
                .mapToLong(m -> m.getFileSize() != null ? m.getFileSize() : 0).sum();

        Map<String, Long> documentsByType = new HashMap<>();
        mediaRepository.countByMediaType().forEach(result ->
                documentsByType.put(result[0].toString(), (Long) result[1]));

        Map<String, Object> stats = new HashMap<>();
        stats.put("totalSpace", totalSpace);
        stats.put("usedSpace", usedSpace);
        stats.put("freeSpace", freeSpace);
        stats.put("usedPercentage", totalSpace > 0 ? (double) usedSpace * 100 / totalSpace : 0);
        stats.put("totalDocuments", mediaRepository.count());
        stats.put("documentsByType", documentsByType);
        return stats;
    }

    @CacheEvict(value = {"mediaContent", "mediaMetadata"}, key = "#mediaId")
    public void deleteMedia(UUID mediaId) {
        Media media = mediaRepository.findById(mediaId)
                .orElseThrow(() -> new RuntimeException("Media not found: " + mediaId));
        try {
            Files.deleteIfExists(rootLocation.resolve(media.getStoredFilename()));
            mediaRepository.delete(media);
            log.info("Media deleted: {}", mediaId);
        } catch (IOException e) {
            throw new RuntimeException("Failed to delete file", e);
        }
    }

    private String getExtension(String filename) {
        if (filename == null || !filename.contains(".")) return "";
        return filename.substring(filename.lastIndexOf("."));
    }
}
