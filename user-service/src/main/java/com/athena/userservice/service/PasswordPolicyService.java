package com.athena.userservice.service;

import com.athena.userservice.model.PasswordPolicy;
import com.athena.userservice.repository.PasswordPolicyRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.regex.Pattern;

@Service
@RequiredArgsConstructor
public class PasswordPolicyService {

    private final PasswordPolicyRepository policyRepository;

    public void validatePassword(String password) {
        PasswordPolicy policy = policyRepository.findAll().stream().findFirst().orElse(null);
        if (policy == null) return;

        if (password.length() < policy.getMinLength()) {
            throw new RuntimeException("Password must be at least " + policy.getMinLength() + " characters long");
        }
        if (policy.isRequireUppercase() && !Pattern.compile("[A-Z]").matcher(password).find()) {
            throw new RuntimeException("Password must contain at least one uppercase letter");
        }
        if (policy.isRequireLowercase() && !Pattern.compile("[a-z]").matcher(password).find()) {
            throw new RuntimeException("Password must contain at least one lowercase letter");
        }
        if (policy.isRequireNumbers() && !Pattern.compile("[0-9]").matcher(password).find()) {
            throw new RuntimeException("Password must contain at least one number");
        }
        if (policy.isRequireSpecialChars()) {
            String specialChars = policy.getSpecialChars() != null && !policy.getSpecialChars().isEmpty()
                    ? Pattern.quote(policy.getSpecialChars())
                    : "!@#$%^&*()_+\\-=\\[\\]{};':\"\\\\|,.<>\\/?";
            if (!Pattern.compile("[" + specialChars + "]").matcher(password).find()) {
                throw new RuntimeException("Password must contain at least one special character");
            }
        }
    }

    public PasswordPolicy getCurrentPolicy() {
        return policyRepository.findAll().stream().findFirst()
                .orElseThrow(() -> new RuntimeException("No password policy configured"));
    }

    public PasswordPolicy updatePolicy(PasswordPolicy newPolicy) {
        PasswordPolicy existing = policyRepository.findAll().stream().findFirst().orElse(new PasswordPolicy());
        existing.setMinLength(newPolicy.getMinLength());
        existing.setRequireUppercase(newPolicy.isRequireUppercase());
        existing.setRequireLowercase(newPolicy.isRequireLowercase());
        existing.setRequireNumbers(newPolicy.isRequireNumbers());
        existing.setRequireSpecialChars(newPolicy.isRequireSpecialChars());
        existing.setExpirationDays(newPolicy.getExpirationDays());
        existing.setSpecialChars(newPolicy.getSpecialChars());
        return policyRepository.save(existing);
    }
}
