---
title: Global Context
description: Load when adding or organizing user-level doctrine shared by ContextKit projects that opt into this source.
load: stub
order: 100
---

# Global Context

This directory owns user-level doctrine shared by ContextKit projects that explicitly opt into this source.

Add a separate context file alongside this file for each durable cross-project rule. Keep project-specific facts in the owning project's `context/` tree, and do not copy global facts into projects.

Use `contextkit guide global-context` before configuring, authoring, validating, or repairing this source.
