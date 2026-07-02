# ADR-0003 Demo 优先使用共享文件系统

## Status

Accepted for demo.

## Context

WES/NIPT 会产生大量文件、日志和报告。对象存储更适合生产，但会增加 demo 初期复杂度。

## Decision

Demo 阶段使用 shared filesystem volume：uploads、runs、reports、logs。数据库只保存路径和 metadata。

## Consequences

优点：

- 简单直接。
- 容易和现有服务器流程整合。
- 方便 debug。

缺点：

- 多机器扩展有限。
- 权限和清理策略需要谨慎。
- 生产化可能需要迁移到对象存储或共享存储。
