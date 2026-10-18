# Hash only the flat messages exchanged with ctk-index-worker, including Symbol.
# Inventory RPCs, status fields, comments and formatting do not affect extraction.
function(ctk_index_protocol_fingerprint protocol output)
  file(READ "${protocol}" source)
  string(REGEX REPLACE "//[^\n]*" "" source "${source}")
  string(REGEX REPLACE [[/[*]([^*]|[*]+[^*/])*[*]+/]] "" source "${source}")
  set(contract "")
  foreach(name Symbol IndexWorkerRequest IndexWorkerTranslationUnit
               IndexWorkerDependency IndexWorkerResponse)
    string(REGEX MATCH "message[ \t\r\n]+${name}[ \t\r\n]*\\{[^{}]*\\}" message "${source}")
    if(NOT message)
      message(FATAL_ERROR "Missing or nested index worker message: ${name}")
    endif()
    string(REGEX REPLACE "[ \t\r\n]" "" message "${message}")
    string(APPEND contract "${message}")
  endforeach()
  string(SHA256 digest "${contract}")
  # Preserve the deployed v1 extractor identity for this exact worker contract.
  # This compatibility anchor avoids a full refresh merely to narrow the hash;
  # any worker/Symbol field change still receives a different fingerprint.
  if(digest STREQUAL "f1c3a79a1bdcef6fe369ab3faffe69bc4e1328db50e83626c233c31ad52a8c03")
    set(digest "7881a179b73526ee65b304d4872ee579a744b318a8d710661270fffcc5c548cd")
  endif()
  set(${output} "${digest}" PARENT_SCOPE)
endfunction()
