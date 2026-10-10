#pragma once

#include "ctk/application/resource_manager.hpp"
#include "ctk/clang/file_discovery.hpp"
#include "ctk/clang/snapshot_resource_scope.hpp"

namespace ctk::application::detail {
inline ctk::clang_layer::SnapshotResourceScope make_snapshot_scope(
    const std::shared_ptr<ResourceManager> &manager, const std::string &owner,
    const std::string &scope_id, const std::string &work_token = {}) {
  return ctk::clang_layer::SnapshotResourceScope(
      scope_id, manager && manager->scope_transient(owner, scope_id),
      [manager, owner, scope_id, work_token](
          const ctk::clang_layer::FileInput &file,
          ctk::cache::SnapshotPtr snapshot, std::function<void()> release) {
        if (!manager) {
          if (release)
            release();
          return;
        }
        const auto identity =
            file.path + "\n" +
            ctk::clang_layer::resolved_compilation_profile(file);
        ctk::match::v1::InputDescriptor input;
        input.set_file_path(file.path);
        auto *profile = input.mutable_profile();
        profile->set_profile_id(
            ctk::clang_layer::resolved_compilation_profile(file));
        profile->set_working_directory(file.working_directory);
        profile->set_compilation_database(file.compilation_database);
        profile->set_frozen(true);
        for (const auto &argument : file.compile_arguments)
          profile->add_compile_arguments(argument);
        if (!scope_id.empty())
          manager->claim_snapshot(owner, scope_id, identity, snapshot,
                                  std::move(release), input);
        manager->register_work_snapshot(owner, work_token, identity,
                                        std::move(snapshot), std::move(input));
      });
}
} // namespace ctk::application::detail
