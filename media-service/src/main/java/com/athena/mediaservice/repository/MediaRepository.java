package com.athena.mediaservice.repository;

import com.athena.mediaservice.model.Media;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Repository
public interface MediaRepository extends JpaRepository<Media, UUID> {

    List<Media> findByCustomerId(Long customerId);

    List<Media> findByCustomerIdAndMediaType(Long customerId, Media.MediaType mediaType);

    boolean existsByCustomerIdAndMediaType(Long customerId, Media.MediaType mediaType);

    List<Media> findByCategory(Media.MediaCategory category);

    List<Media> findByReferenceId(UUID referenceId);

    List<Media> findByCategoryAndReferenceId(Media.MediaCategory category, UUID referenceId);

    List<Media> findByStatus(Media.MediaStatus status);

    @Query("SELECT m FROM Media m WHERE m.tags LIKE %:tag%")
    List<Media> findByTagsContaining(@Param("tag") String tag);

    @Query("SELECT m FROM Media m WHERE " +
            "(:category IS NULL OR m.category = :category) AND " +
            "(:status IS NULL OR m.status = :status) AND " +
            "(:fromDate IS NULL OR m.createdAt >= :fromDate) AND " +
            "(:toDate IS NULL OR m.createdAt <= :toDate)")
    List<Media> searchMedia(
            @Param("category") Media.MediaCategory category,
            @Param("status") Media.MediaStatus status,
            @Param("fromDate") LocalDateTime fromDate,
            @Param("toDate") LocalDateTime toDate);

    @Query("SELECT m.mediaType, COUNT(m) FROM Media m GROUP BY m.mediaType")
    List<Object[]> countByMediaType();

    @Query("SELECT m.category, COUNT(m) FROM Media m GROUP BY m.category")
    List<Object[]> countByCategory();
}
