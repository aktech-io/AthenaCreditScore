package com.athena.userservice.config;

import com.athena.userservice.model.Group;
import com.athena.userservice.model.PasswordPolicy;
import com.athena.userservice.model.Role;
import com.athena.userservice.repository.GroupRepository;
import com.athena.userservice.repository.PasswordPolicyRepository;
import com.athena.userservice.repository.RoleRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class DataInitializer implements CommandLineRunner {

    private final RoleRepository roleRepository;
    private final GroupRepository groupRepository;
    private final PasswordPolicyRepository passwordPolicyRepository;

    @Override
    public void run(String... args) {
        // Athena Credit Score roles
        createRoleIfNotFound("USER",        "Standard internal user");
        createRoleIfNotFound("ADMIN",       "Administrator with full access");
        createRoleIfNotFound("ANALYST",     "Credit analyst — view scores and reports");
        createRoleIfNotFound("VIEWER",      "Read-only access to dashboard");
        createRoleIfNotFound("CREDIT_RISK", "Credit risk officer — model configuration");

        // Athena Credit Score groups
        createGroupIfNotFound("ADMINISTRATORS",     "System administrators");
        createGroupIfNotFound("ANALYSTS",           "Credit analysts team");
        createGroupIfNotFound("CREDIT_RISK_TEAM",   "Credit risk management team");

        // Default password policy
        if (passwordPolicyRepository.count() == 0) {
            log.info("Seeding default password policy");
            passwordPolicyRepository.save(PasswordPolicy.builder()
                    .minLength(8)
                    .requireUppercase(true)
                    .requireLowercase(true)
                    .requireNumbers(true)
                    .requireSpecialChars(false)
                    .expirationDays(90)
                    .build());
        }
    }

    private Role createRoleIfNotFound(String name, String description) {
        return roleRepository.findByName(name).orElseGet(() -> {
            log.info("Seeding role: {}", name);
            return roleRepository.save(Role.builder().name(name).description(description).build());
        });
    }

    private Group createGroupIfNotFound(String name, String description) {
        return groupRepository.findByName(name).orElseGet(() -> {
            log.info("Seeding group: {}", name);
            return groupRepository.save(Group.builder().name(name).description(description).build());
        });
    }
}
