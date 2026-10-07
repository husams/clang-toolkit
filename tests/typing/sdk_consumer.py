"""Pyright consumer contract for the installed Python SDK."""

from collections.abc import Mapping
from typing import assert_type

from clang_toolkit import AsyncClient, Client, MatchValue, ParsedTree
from clang_toolkit._generated.ast.v1 import node_pb2, semantic_pb2
from clang_toolkit._generated.match.v1 import match_result_pb2


def sync_usage(client: Client) -> None:
    tree = client.parse("example.cc", compile_arguments=["-std=c++23"])
    assert_type(tree, ParsedTree[Client])
    with tree.match('functionDecl().bind("f")') as rows:
        assert_type(rows, MatchValue[Client])
        row = rows[0]
        assert_type(row.bindings, Mapping[str, match_result_pb2.MatchBinding])
        binding = row.bindings["f"]
        assert_type(binding.node, node_pb2.AstNode)
        assert_type(binding.qualified_type, semantic_pb2.QualType)
        with row.binding("f").match("callExpr()") as calls:
            assert_type(calls, MatchValue[Client])


async def async_usage(client: AsyncClient) -> None:
    tree = await client.parse("example.cc", working_directory=".")
    assert_type(tree, ParsedTree[AsyncClient])
    async with await tree.match('functionDecl().bind("f")') as rows:
        assert_type(rows, MatchValue[AsyncClient])
        row = rows[0]
        assert_type(row.bindings, Mapping[str, match_result_pb2.MatchBinding])
        binding = row.bindings["f"]
        assert_type(binding.node, node_pb2.AstNode)
        assert_type(binding.qualified_type, semantic_pb2.QualType)
        async with await row.binding("f").match("callExpr()") as calls:
            assert_type(calls, MatchValue[AsyncClient])


async def convenience_match(client: Client, async_client: AsyncClient) -> None:
    sync_value = client.match("functionDecl()", file="example.cc")
    assert_type(sync_value, MatchValue[Client])
    async_value = await async_client.match("functionDecl()", file="example.cc")
    assert_type(async_value, MatchValue[AsyncClient])
