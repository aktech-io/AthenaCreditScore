package com.athena.userservice.repository;

import com.athena.userservice.model.PasswordPolicy;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PasswordPolicyRepository extends JpaRepository<PasswordPolicy, Long> {
}
