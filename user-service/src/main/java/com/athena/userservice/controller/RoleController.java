package com.athena.userservice.controller;

import com.athena.userservice.model.Role;
import com.athena.userservice.repository.RoleRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/admin/roles")
@RequiredArgsConstructor
@Tag(name = "Role Management", description = "Admin endpoints for managing roles")
public class RoleController {

    private final RoleRepository roleRepository;

    @GetMapping
    @Operation(summary = "List all roles")
    public ResponseEntity<List<Role>> getAll() {
        return ResponseEntity.ok(roleRepository.findAll());
    }

    @PostMapping
    @Operation(summary = "Create a new role")
    public ResponseEntity<Role> create(@RequestBody Role role) {
        return ResponseEntity.ok(roleRepository.save(role));
    }
}
