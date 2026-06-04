# Expense Splitter — Product Requirements Document

## Overview

Expense Splitter is a web application that helps groups of people track shared expenses and settle debts. Users create groups (e.g., a trip, a household, a dinner), add members, and log expenses with flexible split rules — equal, exact amounts, or percentage-based. The app continuously calculates net balances across the group and suggests the minimum number of transactions needed for everyone to settle up.

## Key Capabilities

The application is organized around three core areas. First, a **Groups & Expenses API** that handles creating groups, managing members, and recording expenses with their split details. Second, a **Balance Calculation Engine** that computes who owes whom, simplifies debts across the group, and produces optimized settlement suggestions. Third, a **Dashboard & Settlement UI** that gives users a clear view of group balances, individual debts, and a one-click flow to mark settlements as complete. The tech stack is flexible, but the app should be built as a single-page frontend backed by a REST API with persistent storage.
