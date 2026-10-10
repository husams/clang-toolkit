#pragma once

#include "ctk/application/resource_manager.hpp"
#include "ctk/clang/file_discovery.hpp"
#include "ctk/clang/snapshot_resource_scope.hpp"

namespace ctk::application::detail {
inline ctk::match::v1::InputDescriptor snapshot_input_descriptor(
    const ctk::clang_layer::FileInput &file,
    const std::vector<ctk::match::v1::InputDescriptor> &source_inputs) {
  const auto profile_id = ctk::clang_layer::resolved_compilation_profile(file);
  for (const auto &candidate : source_inputs) {
    if (candidate.file_path() != file.path || !candidate.has_profile())
      continue;
    const auto &profile = candidate.profile();
    if (profile.profile_id() == profile_id &&
        profile.working_directory() == file.working_directory &&
        profile.compilation_database() == file.compilation_database &&
        profile.frozen() == file.compilation_profile_frozen &&
        std::vector<std::string>(profile.compile_arguments().begin(),
                                 profile.compile_arguments().end()) ==
            file.compile_arguments)
      return candidate;
  }
  ctk::match::v1::InputDescriptor input;
  input.set_file_path(file.path);
  auto *profile = input.mutable_profile();
  profile->set_profile_id(profile_id);
  profile->set_working_directory(file.working_directory);
  profile->set_compilation_database(file.compilation_database);
  profile->set_frozen(true);
  for (const auto &argument : file.compile_arguments)
    profile->add_compile_arguments(argument);
  return input;
}
inline ctk::clang_layer::SnapshotResourceScope make_snapshot_scope(
    const std::shared_ptr<ResourceManager> &manager, const std::string &owner,
    const std::string &scope_id, const std::string &work_token = {},
    const std::vector<ctk::match::v1::InputDescriptor> &source_inputs = {}) {
  return ctk::clang_layer::SnapshotResourceScope(
      scope_id, manager && manager->scope_transient(owner, scope_id),
      [manager, owner, scope_id, work_token, source_inputs](
          const ctk::clang_layer::FileInput &file,
          ctk::cache::SnapshotPtr snapshot, std::function<void()> release) {
        if (!manager) {
          if (release)
            release();
          return;
        }
        auto input = snapshot_input_descriptor(file, source_inputs);
        const auto identity = ctk::application::input_identity(input);
        if (!scope_id.empty())
          manager->claim_snapshot(owner, scope_id, identity, snapshot,
                                  std::move(release), input);
        manager->register_work_snapshot(owner, work_token, identity,
                                        std::move(snapshot), std::move(input));
      });
}
inline std::unique_ptr<ctk::clang_layer::SnapshotResourceScope>
make_snapshot_scope_ptr(
    const std::shared_ptr<ResourceManager> &manager, const std::string &owner,
    const std::string &scope_id, const std::string &work_token = {},
    const std::vector<ctk::match::v1::InputDescriptor> &source_inputs = {}) {
  const auto claim = [manager, owner, scope_id, work_token,
                      source_inputs](const ctk::clang_layer::FileInput &file,
                                     ctk::cache::SnapshotPtr snapshot,
                                     std::function<void()> release) {
    if (!manager) {
      if (release)
        release();
      return;
    }
    auto input = snapshot_input_descriptor(file, source_inputs);
    const auto identity = ctk::application::input_identity(input);
    if (!scope_id.empty())
      manager->claim_snapshot(owner, scope_id, identity, snapshot,
                              std::move(release), input);
    manager->register_work_snapshot(owner, work_token, identity,
                                    std::move(snapshot), std::move(input));
  };
  return std::make_unique<ctk::clang_layer::SnapshotResourceScope>(
      scope_id, manager && manager->scope_transient(owner, scope_id), claim);
}
} // namespace ctk::application::detail
