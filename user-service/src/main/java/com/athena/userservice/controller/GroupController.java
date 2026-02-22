package com.athena.userservice.controller;

import com.athena.userservice.model.Group;
import com.athena.userservice.model.Role;
import com.athena.userservice.repository.GroupRepository;
import com.athena.userservice.repository.RoleRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/admin/groups")
@RequiredArgsConstructor
@Tag(name = "Group Management", description = "Admin endpoints for managing user groups")
public class GroupController {

    private final GroupRepository groupRepository;
    private final RoleRepository roleRepository;

    @GetMapping
    @Operation(summary = "List all groups")
    public ResponseEntity<List<Group>> getAll() {
        return ResponseEntity.ok(groupRepository.findAll());
    }

    @PostMapping
    @Operation(summary = "Create a new group")
    public ResponseEntity<Group> create(@RequestBody Group group) {
        return ResponseEntity.ok(groupRepository.save(group));
    }

    @PostMapping("/{groupId}/roles/{roleId}")
    @Operation(summary = "Assign a role to a group")
    public ResponseEntity<Group> assignRole(@PathVariable Long groupId, @PathVariable Long roleId) {
        Group group = groupRepository.findById(groupId).orElseThrow(() -> new RuntimeException("Group not found"));
        Role role = roleRepository.findById(roleId).orElseThrow(() -> new RuntimeException("Role not found"));
        group.getRoles().add(role);
        return ResponseEntity.ok(groupRepository.save(group));
    }

    @DeleteMapping("/{groupId}/roles/{roleId}")
    @Operation(summary = "Remove a role from a group")
    public ResponseEntity<Group> removeRole(@PathVariable Long groupId, @PathVariable Long roleId) {
        Group group = groupRepository.findById(groupId).orElseThrow(() -> new RuntimeException("Group not found"));
        Role role = roleRepository.findById(roleId).orElseThrow(() -> new RuntimeException("Role not found"));
        group.getRoles().remove(role);
        return ResponseEntity.ok(groupRepository.save(group));
    }
}
