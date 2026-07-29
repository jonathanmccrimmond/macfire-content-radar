#!/usr/bin/env python3
"""Build the MacFire social preview from markdown draft posts.

Usage:
  python3 scripts/build_preview.py
  python3 scripts/build_preview.py --watch
"""

from __future__ import annotations

import argparse
import ast
import html
import json
import re
import sys
import time
from pathlib import Path
from datetime import date, datetime

import yaml


ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "content" / "posts"
OUTPUT_PATH = ROOT / "preview" / "index.html"


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MacFire Content Radar - Preview</title>
  <link rel="icon" type="image/svg+xml" href="favicon.svg" />
  <link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png" />
  <link rel="apple-touch-icon" href="apple-touch-icon.png" />
  <style>
    :root {
      --bg: #f4e9d8;
      --surface: #fafaf7;
      --surface-soft: #f8f1e7;
      --text: #111111;
      --muted: #5a5a57;
      --line: #e6e2d8;
      --brand-primary: #c31e1f;
      --brand-deep: #9b1718;
      --linkedin: #0a66c2;
      --facebook: #1877f2;
      --x: #0f1419;
      --x-blue: #1d9bf0;
    }
    * { box-sizing: border-box; }
    html { min-width: 0; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }
    a { overflow-wrap: anywhere; }
    .wrap { max-width: 1420px; margin: 0 auto; padding: 14px 18px 32px; }
    .hero {
      display: flex; align-items: center; justify-content: space-between;
      gap: 14px; margin-bottom: 12px;
      padding-bottom: 10px; border-bottom: 1px solid rgba(155, 23, 24, 0.18);
    }
    .brand-row { display: flex; align-items: center; gap: 14px; min-width: 0; }
    .brand-mark {
      height: 44px; width: auto; display: block;
      border-radius: 4px; flex: 0 0 auto;
    }
    .eyebrow {
      display: inline-flex; align-items: center; gap: 8px;
      color: var(--brand-primary); font-weight: 800;
      text-transform: uppercase; letter-spacing: 0; font-size: 11px;
    }
    h1 {
      margin: 0; font-size: 21px;
      line-height: 1.08; letter-spacing: 0; max-width: 24ch;
    }
    .lede { display: none; }
    .dashboard-meta {
      display: flex; flex-wrap: wrap; gap: 10px;
      margin-top: 0; color: var(--muted); font-size: 12px;
    }
    .metric {
      display: inline-flex; align-items: center; gap: 8px;
      border: 1px solid var(--line); background: rgba(250,250,247,0.82);
      padding: 6px 9px; border-radius: 8px;
    }
    .metric strong { color: var(--text); font-weight: 700; }
    .metric-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--brand-deep); }
    .metric-dot.fb { background: var(--facebook); }
    .metric-dot.x { background: var(--x); }
    .metric-dot.li { background: var(--linkedin); }
    @media (max-width: 700px) {
      .wrap { padding: 12px 12px 32px; }
      .hero { display: grid; }
      .brand-mark { height: 36px; }
      h1 { font-size: 18px; }
    }
    .section {
      margin-top: 26px; padding-top: 26px;
      border-top: 1px solid rgba(155, 23, 24, 0.12);
    }
    .section-head {
      display: flex; justify-content: space-between; align-items: end;
      gap: 14px; margin-bottom: 16px; flex-wrap: wrap;
    }
    .section-head h2 { margin: 0; font-size: 22px; letter-spacing: 0; line-height: 1.16; }
    .section-head .meta { color: var(--muted); font-size: 13px; }
    .post-grid {
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px; align-items: start;
    }
    .platform-card { min-width: 0; }
    @media (max-width: 1180px) { .post-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 780px) { .post-grid { grid-template-columns: minmax(0, 1fr); } }
    .platform-label {
      font-size: 11px; font-weight: 800; letter-spacing: 0;
      text-transform: uppercase; color: var(--muted); margin-bottom: 8px;
    }
    .platform-label.fb { color: var(--facebook); }
    .platform-label.x { color: var(--x); }
    .platform-label.li { color: var(--linkedin); }

    /* ===== Facebook post ===== */
    .fb-post {
      width: 100%; min-width: 0;
      background: #fff; border-radius: 8px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.2);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Historic", "Segoe UI", Helvetica, Arial, sans-serif;
      color: #050505; font-size: 15px; line-height: 1.3333;
      overflow: hidden;
    }
    .fb-header { display: flex; align-items: center; padding: 12px 16px 0; }
    .fb-avatar {
      width: 40px; height: 40px; border-radius: 50%;
      background: #f0f2f5 center/cover no-repeat;
      flex: 0 0 auto; border: 1px solid #dadde1;
    }
    .fb-meta { margin-left: 8px; flex: 1; min-width: 0; }
    .fb-name {
      font-weight: 600; color: #050505; font-size: 15px;
      line-height: 1.2; cursor: pointer;
    }
    .fb-name:hover { text-decoration: underline; }
    .fb-sub {
      display: flex; align-items: center; gap: 4px;
      color: #65676b; font-size: 13px; margin-top: 2px;
    }
    .fb-sub svg { width: 12px; height: 12px; fill: #65676b; }
    .fb-actions-top {
      display: flex; gap: 4px; color: #65676b;
      align-self: flex-start; margin-top: -4px;
    }
    .fb-icon-btn {
      width: 36px; height: 36px; border-radius: 50%;
      display: grid; place-items: center; cursor: pointer;
      color: #65676b;
    }
    .fb-icon-btn:hover { background: #f2f2f2; }
    .fb-icon-btn svg { width: 20px; height: 20px; fill: currentColor; }
    .fb-body {
      padding: 12px 16px 12px; font-size: 15px; color: #050505;
      white-space: pre-wrap; overflow-wrap: anywhere;
    }
    .fb-body p { margin: 0 0 0.5em; }
    .fb-body p:last-child { margin-bottom: 0; }
    .fb-image {
      width: 100%; display: block; max-height: 500px; object-fit: cover;
      border-top: 1px solid #ced0d4; border-bottom: 1px solid #ced0d4;
    }
    .fb-link-preview {
      background: #f0f2f5; border-top: 1px solid #ced0d4;
      border-bottom: 1px solid #ced0d4; padding: 10px 16px;
    }
    .fb-link-domain { color: #65676b; text-transform: uppercase; font-size: 13px; }
    .fb-link-title { color: #050505; font-weight: 600; font-size: 17px; margin-top: 2px; }
    .fb-stats {
      display: flex; justify-content: space-between; align-items: center;
      gap: 10px; flex-wrap: wrap;
      padding: 10px 16px 6px; color: #65676b; font-size: 14px;
    }
    .fb-reactions { display: flex; align-items: center; gap: 4px; min-width: 0; }
    .fb-reaction-pill {
      display: inline-flex; align-items: center; gap: -2px;
    }
    .fb-reaction-pill img { width: 18px; height: 18px; margin-left: -2px; }
    .fb-reaction-emoji {
      width: 18px; height: 18px; border-radius: 50%; display: inline-grid;
      place-items: center; font-size: 11px; margin-left: -3px; border: 2px solid #fff;
    }
    .fb-reaction-emoji:first-child { margin-left: 0; }
    .fb-reaction-emoji.like { background: linear-gradient(180deg,#3b82f6,#1d4ed8); color: #fff; }
    .fb-reaction-emoji.love { background: linear-gradient(180deg,#f87171,#dc2626); color: #fff; }
    .fb-reaction-count { margin-left: 6px; }
    .fb-action-bar {
      display: flex; border-top: 1px solid #ced0d4; margin: 0 16px;
      padding: 4px 0;
    }
    .fb-action {
      flex: 1; min-width: 0; display: flex; align-items: center; justify-content: center; gap: 6px;
      padding: 8px 4px; color: #65676b; font-weight: 600; cursor: pointer; font-size: 14px;
      border-radius: 4px;
    }
    .fb-action:hover { background: #f2f2f2; }
    .fb-action svg { width: 20px; height: 20px; fill: #65676b; }

    /* ===== LinkedIn post ===== */
    .li-post {
      width: 100%; min-width: 0;
      background: #fff; border: 1px solid rgba(0,0,0,0.08); border-radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, Roboto, Helvetica, Arial, sans-serif;
      color: rgba(0,0,0,0.9); overflow: hidden;
      box-shadow: 0 0 0 1px rgba(0,0,0,0.08);
    }
    .li-header { display: flex; padding: 12px 16px 0; align-items: flex-start; }
    .li-avatar {
      width: 48px; height: 48px; border-radius: 50%;
      background: #e9e5df center/cover no-repeat;
      flex: 0 0 auto; border: 1px solid rgba(0,0,0,0.08);
    }
    .li-meta { margin-left: 8px; flex: 1; min-width: 0; }
    .li-name {
      font-weight: 600; color: rgba(0,0,0,0.9); font-size: 14px;
      line-height: 1.4; cursor: pointer;
    }
    .li-name:hover { color: #0a66c2; text-decoration: underline; }
    .li-tag { color: rgba(0,0,0,0.6); font-size: 12px; line-height: 1.33; margin-top: 1px; }
    .li-sub {
      color: rgba(0,0,0,0.6); font-size: 12px; margin-top: 1px;
      display: flex; align-items: center; gap: 4px;
    }
    .li-sub svg { width: 12px; height: 12px; fill: rgba(0,0,0,0.6); }
    .li-follow {
      color: #0a66c2; font-weight: 600; font-size: 15px;
      display: flex; align-items: center; gap: 6px; padding: 4px 8px;
      cursor: pointer; border-radius: 4px;
    }
    .li-follow:hover { background: rgba(112,181,249,0.2); }
    .li-more {
      color: rgba(0,0,0,0.6); padding: 4px; margin-left: 4px;
      cursor: pointer; border-radius: 50%;
    }
    .li-more:hover { background: rgba(0,0,0,0.08); }
    .li-more svg { width: 20px; height: 20px; fill: currentColor; }
    .li-body {
      padding: 12px 16px 8px; font-size: 14px; line-height: 1.4286;
      color: rgba(0,0,0,0.9); white-space: pre-wrap; overflow-wrap: anywhere;
    }
    .li-body p { margin: 0 0 0.6em; }
    .li-body p:last-child { margin-bottom: 0; }
    .li-hashtags { color: #0a66c2; font-weight: 600; padding: 0 16px 12px; font-size: 14px; }
    .li-hashtags span { margin-right: 6px; cursor: pointer; }
    .li-hashtags span:hover { text-decoration: underline; }
    .li-image { width: 100%; display: block; max-height: 540px; object-fit: cover; }
    .li-stats {
      display: flex; justify-content: space-between; align-items: center;
      gap: 10px; flex-wrap: wrap;
      padding: 8px 16px; color: rgba(0,0,0,0.6); font-size: 12px;
    }
    .li-reactions { display: flex; align-items: center; gap: 0; }
    .li-reactions span { margin-left: 4px; }
    .li-reaction-emoji {
      width: 16px; height: 16px; border-radius: 50%; display: inline-grid;
      place-items: center; font-size: 10px; margin-left: -3px; border: 1.5px solid #fff;
    }
    .li-reaction-emoji:first-child { margin-left: 0; }
    .li-reaction-emoji.like { background: #0a66c2; color: #fff; }
    .li-reaction-emoji.celebrate { background: #6dae4f; color: #fff; }
    .li-reaction-emoji.insight { background: #f5bb5c; color: #fff; }
    .li-divider { border-top: 1px solid rgba(0,0,0,0.08); margin: 0 16px; }
    .li-action-bar {
      display: flex; padding: 4px 12px;
    }
    .li-action {
      flex: 1; min-width: 0; display: flex; align-items: center; justify-content: center; gap: 4px;
      padding: 10px 4px; color: rgba(0,0,0,0.6); font-weight: 600; cursor: pointer; font-size: 14px;
      border-radius: 4px;
    }
    .li-action:hover { background: rgba(0,0,0,0.08); }
    .li-action svg { width: 20px; height: 20px; fill: rgba(0,0,0,0.6); }

    /* ===== X post ===== */
    .x-post {
      width: 100%; min-width: 0;
      background: #fff; border: 1px solid #cfd9de; border-radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--x); overflow: hidden;
    }
    .x-header { display: flex; gap: 10px; padding: 12px 14px 0; align-items: flex-start; min-width: 0; }
    .x-avatar {
      width: 40px; height: 40px; border-radius: 50%;
      background: #eff3f4 center/cover no-repeat;
      flex: 0 0 auto; border: 1px solid #cfd9de;
    }
    .x-meta { flex: 1; min-width: 0; }
    .x-name-line {
      display: flex; align-items: baseline; gap: 4px; min-width: 0;
      font-size: 15px; line-height: 1.25;
    }
    .x-name { font-weight: 700; color: var(--x); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .x-handle { color: #536471; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .x-more { color: #536471; padding: 4px; border-radius: 50%; margin-top: -4px; flex: 0 0 auto; }
    .x-more svg { width: 20px; height: 20px; fill: currentColor; }
    .x-body {
      padding: 6px 14px 0 64px; font-size: 15px; line-height: 1.33;
      white-space: pre-wrap; overflow-wrap: anywhere;
    }
    .x-body p { margin: 0 0 0.56em; }
    .x-body p:last-child { margin-bottom: 0; }
    .x-body a { color: var(--x-blue); text-decoration: none; }
    .x-count {
      padding: 8px 14px 8px 64px; color: #536471; font-size: 12px;
    }
    .x-stats {
      display: flex; flex-wrap: wrap; gap: 10px 14px;
      border-top: 1px solid #eff3f4; margin: 0 14px;
      padding: 10px 0; color: #536471; font-size: 13px;
    }
    .x-stat strong { color: var(--x); font-weight: 700; }
    .x-action-bar {
      display: flex; justify-content: space-between; gap: 4px;
      border-top: 1px solid #eff3f4; padding: 4px 10px 8px;
    }
    .x-action {
      min-width: 0; display: flex; align-items: center; justify-content: center;
      gap: 5px; color: #536471; font-size: 13px; padding: 7px 4px; border-radius: 4px; flex: 1;
    }
    .x-action svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round; }
    .x-action.like:hover { color: #f91880; background: rgba(249, 24, 128, 0.1); }
    .x-action.repost:hover { color: #00ba7c; background: rgba(0, 186, 124, 0.1); }
    .x-action.reply:hover,
    .x-action.views:hover,
    .x-action.share:hover { color: var(--x-blue); background: rgba(29, 155, 240, 0.1); }
    @media (max-width: 480px) {
      .fb-header, .li-header { padding-left: 12px; padding-right: 12px; }
      .fb-body, .li-body { padding-left: 12px; padding-right: 12px; }
      .fb-stats, .li-stats { padding-left: 12px; padding-right: 12px; font-size: 12px; }
      .fb-action-bar, .li-divider { margin-left: 12px; margin-right: 12px; }
      .li-action-bar { padding-left: 8px; padding-right: 8px; }
      .fb-action span, .li-action span, .x-action span { display: none; }
      .x-body, .x-count { padding-left: 14px; }
      .x-header { padding-left: 14px; padding-right: 14px; }
    }

    .review-shell { display: grid; gap: 16px; }
    .review-desk {
      display: grid; grid-template-columns: minmax(520px, 0.92fr) minmax(420px, 1.08fr);
      gap: 16px; align-items: start;
    }
    .calendar-shell,
    .approval-shell,
    .history-shell {
      border: 1px solid rgba(155, 23, 24, 0.18);
      background: rgba(250, 250, 247, 0.78);
      border-radius: 8px;
      padding: 12px;
    }
    .calendar-head,
    .history-head {
      display: flex; align-items: center; justify-content: space-between;
      gap: 10px; margin-bottom: 10px; flex-wrap: wrap;
    }
    .approval-head { margin-bottom: 8px; }
    .calendar-head h2,
    .approval-head h2,
    .history-head h2 { margin: 0; font-size: 18px; line-height: 1.16; }
    .small-meta { color: var(--muted); font-size: 12px; }
    .month-controls { display: flex; gap: 6px; align-items: center; }
    .month-btn {
      width: 34px; height: 34px; border: 1px solid rgba(17,17,17,0.14);
      border-radius: 8px; background: #fff; color: var(--text);
      font: inherit; font-weight: 900; cursor: pointer;
    }
    .month-btn:hover { filter: brightness(0.97); }
    .status-legend { display: flex; gap: 8px; flex-wrap: wrap; }
    .legend-item {
      display: inline-flex; align-items: center; gap: 6px;
      font-size: 12px; color: var(--muted);
    }
    .status-dot { width: 9px; height: 9px; border-radius: 50%; background: #8f949b; }
    .status-dot.draft { background: #8f949b; }
    .status-dot.approved { background: #18864b; }
    .status-dot.published { background: #1877f2; }
    .status-dot.declined { background: #9b1718; }
    .calendar-grid {
      display: grid; grid-template-columns: repeat(7, minmax(0, 1fr));
      border: 1px solid var(--line); border-radius: 8px; overflow: hidden;
      background: var(--surface);
    }
    .calendar-month { margin-top: 10px; }
    .weekday {
      padding: 6px; background: #111; color: #fff;
      font-size: 11px; font-weight: 800; text-transform: uppercase;
    }
    .calendar-day {
      min-height: 80px; padding: 6px; border-top: 1px solid var(--line);
      border-right: 1px solid var(--line); background: #fff;
    }
    .calendar-day:nth-child(7n) { border-right: 0; }
    .calendar-day.is-muted { background: #f6f4ef; color: #8b8b87; }
    .day-number { font-size: 12px; font-weight: 800; margin-bottom: 6px; }
    .calendar-post {
      width: 100%; min-width: 0; text-align: left; border: 1px solid transparent;
      border-left: 4px solid #8f949b; background: #fafaf7; color: var(--text);
      border-radius: 6px; padding: 5px 6px; margin-top: 4px; cursor: pointer;
      font: inherit; font-size: 11px; line-height: 1.18;
    }
    .calendar-post:hover,
    .calendar-post.is-selected { border-color: rgba(17,17,17,0.18); background: #fff; }
    .calendar-post[data-status="approved"] { border-left-color: #18864b; }
    .calendar-post[data-status="published"] { border-left-color: #1877f2; }
    .calendar-post[data-status="declined"] { border-left-color: #9b1718; }
    .calendar-post-title {
      display: block; overflow: hidden; text-overflow: ellipsis;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    }
    .calendar-month { display: none; }
    .calendar-month.is-active { display: block; }
    .approval-card,
    .history-card {
      border: 1px solid rgba(17,17,17,0.1); background: var(--surface);
      border-radius: 8px; padding: 12px; display: grid; gap: 12px;
    }
    .approval-card { display: none; }
    .approval-card.is-active { display: grid; }
    .review-card-head,
    .approval-card-head {
      display: flex; justify-content: space-between; gap: 12px; align-items: start;
    }
    .review-card h3,
    .approval-card h3,
    .history-card h3 { margin: 0; font-size: 17px; line-height: 1.2; }
    .status-pill {
      flex: 0 0 auto; display: inline-flex; align-items: center; gap: 6px;
      min-height: 26px; padding: 4px 8px; border-radius: 999px;
      background: #ece9e0; color: #30302e; font-size: 12px; font-weight: 800;
      text-transform: capitalize;
    }
    .status-pill.approved { background: #dff3e8; color: #105a34; }
    .status-pill.published { background: #e1efff; color: #0a4f96; }
    .status-pill.declined { background: #f6dede; color: #7a1112; }
    .freshness-pill {
      display: inline-flex; align-items: center; width: fit-content;
      min-height: 24px; padding: 3px 8px; border-radius: 999px;
      font-size: 11px; font-weight: 800;
    }
    .freshness-pill.fresh { background: #dff3e8; color: #105a34; }
    .freshness-pill.ageing { background: #fff3cf; color: #735000; }
    .freshness-pill.stale { background: #f6dede; color: #7a1112; }
    .freshness-pill.unknown { background: #ece9e0; color: #30302e; }
    .review-card-meta { display: grid; gap: 3px; color: var(--muted); font-size: 12px; }
    .canonical-preview,
    .approval-preview { max-height: 430px; overflow: auto; border-radius: 8px; }
    .open-detail-btn,
    .decision-btn,
    .copy-btn,
    .platform-tab {
      border: 1px solid rgba(17,17,17,0.14); border-radius: 8px;
      background: #fff; color: var(--text); font: inherit; font-weight: 800;
      min-height: 40px; padding: 8px 12px; cursor: pointer;
    }
    .open-detail-btn { width: 100%; background: #111; color: #fff; }
    .open-detail-btn:hover,
    .decision-btn:hover,
    .copy-btn:hover,
    .platform-tab:hover { filter: brightness(0.97); }
    .review-context {
      display: grid; gap: 8px; padding: 0 2px;
    }
    .review-context-row {
      display: grid; grid-template-columns: 82px minmax(0, 1fr);
      gap: 10px; align-items: start;
      color: var(--muted); font-size: 13px;
    }
    .review-context-row strong {
      color: var(--text); font-size: 12px; text-transform: uppercase;
    }
    .detail-text { color: var(--muted); font-size: 13px; }
    .detail-text p { margin: 0 0 8px; }
    .detail-text p:last-child { margin-bottom: 0; }
    .detail-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .decision-btn.approve { background: #18864b; border-color: #18864b; color: #fff; }
    .decision-btn.decline { background: #9b1718; border-color: #9b1718; color: #fff; }
    .status-message { min-height: 20px; color: var(--muted); font-size: 13px; }
    .card-image { margin: 4px 0 16px; max-width: 360px; }
    .ci-stage {
      position: relative; width: 100%; aspect-ratio: 1080 / 1350;
      border-radius: 10px; overflow: hidden; border: 1px solid var(--border);
      background: #0b0e16; container-type: inline-size;
    }
    .ci-photo {
      position: absolute; inset: 0; width: 100%; height: 100%;
      object-fit: cover; display: block; transition: opacity .2s ease;
    }
    .ci-photo.is-loading { opacity: 0.4; }
    .ci-overlay { position: absolute; inset: 0; pointer-events: none; }
    .ci-scrim {
      position: absolute; inset: 0;
      background: linear-gradient(to bottom,
        rgba(8,10,16,0) 40%, rgba(8,10,16,0.28) 58%,
        rgba(8,10,16,0.72) 80%, rgba(8,10,16,0.92) 100%);
    }
    .ci-frame {
      position: absolute; inset: 0; display: flex; flex-direction: column;
      justify-content: flex-end; padding: 7cqw;
    }
    .ci-rule { width: 8cqw; height: 0.7cqw; background: #C31E1F; border-radius: 2px; margin-bottom: 3cqw; }
    .ci-headline {
      color: #fff; font-weight: 800; font-size: 6.6cqw; line-height: 1.05;
      letter-spacing: -0.02em; text-shadow: 0 0.2cqw 2cqw rgba(0,0,0,0.4);
    }
    .ci-headline .hl { color: #C31E1F; }
    .ci-footer {
      margin-top: 4.6cqw; padding-top: 3cqw; border-top: 1px solid rgba(255,255,255,0.22);
      display: flex; align-items: center; justify-content: space-between;
    }
    .ci-logo { height: 9.5cqw; width: auto; display: block; border-radius: 1cqw; }
    .ci-phone { color: #fff; font-weight: 800; font-size: 3cqw; letter-spacing: 0.01em; }
    .image-review-actions {
      display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
      margin-top: 8px;
    }
    .image-regen-btn {
      border: 1px solid rgba(17,17,17,0.14); border-radius: 8px;
      background: #fff; color: var(--text); font: inherit; font-weight: 800;
      min-height: 34px; padding: 6px 10px; cursor: pointer; font-size: 12px;
    }
    .image-regen-btn:hover { filter: brightness(0.97); }
    .image-regen-btn:disabled { opacity: 0.55; cursor: default; }
    .ci-picker { display: flex; gap: 6px; margin-top: 8px; }
    .ci-candidate {
      flex: 1; aspect-ratio: 4 / 5; border-radius: 6px; overflow: hidden;
      cursor: pointer; border: 2px solid transparent; position: relative;
      transition: border-color .15s;
    }
    .ci-candidate:hover { border-color: rgba(0,0,0,0.25); }
    .ci-candidate.is-selected { border-color: #18864b; }
    .ci-candidate img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .ci-candidate-credit {
      position: absolute; bottom: 0; left: 0; right: 0;
      background: rgba(0,0,0,0.6); color: #fff; font-size: 9px; padding: 2px 4px;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .sync-warning { background: #7a1112; color: #fff; padding: 10px 16px; text-align: center; font-size: 13px; }
    .platform-toolbar {
      display: flex; align-items: center; justify-content: space-between;
      gap: 10px; flex-wrap: wrap;
    }
    .platform-tabs { display: flex; gap: 8px; flex-wrap: wrap; }
    .platform-tab.is-active { background: #111; color: #fff; }
    .approval-actions { display: grid; gap: 10px; }
    .copy-btn {
      min-height: 32px; padding: 5px 10px; font-size: 12px;
      margin-left: auto;
    }
    .platform-version { display: none; }
    .platform-version.is-active { display: block; }
    .empty-approval {
      display: none; border: 1px dashed rgba(17,17,17,0.2); border-radius: 8px;
      background: #fff; padding: 18px; color: var(--muted);
    }
    .empty-approval.is-active { display: block; }
    .history-grid {
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .history-card { cursor: pointer; text-align: left; font: inherit; color: var(--text); }
    .history-card[data-status="draft"] { display: none; }
    @media (max-width: 980px) {
      .review-desk, .approval-meta-grid, .history-grid { grid-template-columns: minmax(0, 1fr); }
      .calendar-day { min-height: 96px; }
    }
    @media (max-width: 640px) {
      .calendar-shell, .approval-shell, .history-shell { padding: 10px; }
      .calendar-grid { display: block; border: 0; background: transparent; }
      .weekday { display: none; }
      .calendar-day {
        min-height: auto; border: 1px solid var(--line); border-radius: 8px;
        margin-bottom: 8px;
      }
      .calendar-day.is-muted:empty { display: none; }
      .review-card-head { display: grid; }
      .review-context-row { grid-template-columns: minmax(0, 1fr); gap: 2px; }
      .detail-actions { grid-template-columns: minmax(0, 1fr); }
      .platform-toolbar { display: grid; }
      .copy-btn { width: 100%; margin-left: 0; }
    }

    .sources-note {
      margin-top: 0; color: var(--muted); font-size: 12px;
      padding: 0 2px;
    }
    .sources-note a { color: var(--linkedin); text-decoration: none; }
    .sources-note a:hover { text-decoration: underline; }
    .note { margin-top: 28px; color: var(--muted); font-size: 13px; }
    code {
      background: rgba(19,34,56,0.06); padding: 0 4px; border-radius: 4px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="brand-row">
        <svg class="brand-mark" viewBox="0 0 270 100" aria-label="MacFire Ltd, Fire Protection Company" xmlns="http://www.w3.org/2000/svg">
          <rect width="270" height="100" fill="#1A1F3C"/>
          <rect x="2" y="69" width="266" height="29" fill="#ffffff"/>
          <text x="7" y="57" font-family="Impact,'Arial Black',sans-serif" font-size="46" fill="#ffffff" textLength="107" lengthAdjust="spacingAndGlyphs">Mac</text>
          <text x="119" y="57" font-family="Impact,'Arial Black',sans-serif" font-size="46" fill="#ffffff" textLength="92" lengthAdjust="spacingAndGlyphs">Fire</text>
          <text x="213" y="57" font-family="Impact,'Arial Black',sans-serif" font-size="34" fill="#ffffff" textLength="53" lengthAdjust="spacingAndGlyphs">Ltd</text>
          <text x="135" y="83" text-anchor="middle" dominant-baseline="central" font-family="Arial,Helvetica,sans-serif" font-weight="bold" font-size="17" fill="#C31E1F" letter-spacing="1.5">Fire Protection Company</text>
        </svg>
        <div>
          <div class="eyebrow">MacFire Content Radar</div>
        </div>
      </div>
      <p class="lede">Official fire-safety and building-standards updates, drafted for Facebook, LinkedIn, and X with approval controls now and guarded autoposting ready for the Social Media Agent stage.</p>
      <div class="dashboard-meta">
        <div class="metric"><span class="metric-dot"></span><strong>__POST_COUNT__</strong> draft topics</div>
        <div class="metric"><span class="metric-dot fb"></span>Facebook</div>
        <div class="metric"><span class="metric-dot x"></span>X</div>
        <div class="metric"><span class="metric-dot li"></span>LinkedIn</div>
      </div>
    </div>

    <div class="review-shell">
__SECTIONS__
    </div>

    <p class="note">
      Generated from __POST_COUNT__ markdown draft file(s). Content calendar runs to 31 December __CUTOFF_YEAR__.
    </p>
  </div>
  <script>
    window.CONTENT_RADAR_POSTS = __POSTS_JSON__;
  </script>
  <script src="supabase-config.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
  <script src="supabase.js"></script>
  <script>
    const posts = window.CONTENT_RADAR_POSTS || [];
    const radarStatus = window.ContentRadarStatus;

    function statusLabel(status) {
      return (status || "draft").replace(/^./, (letter) => letter.toUpperCase());
    }

    let activeMonthIndex = Number(document.querySelector("[data-active-month-index]")?.dataset.activeMonthIndex || 0);
    let activeReviewSlug = null;

    function applyStatus(slug, status) {
      const post = posts.find((item) => item.slug === slug);
      if (post) post.status = status;
      document.querySelectorAll(`[data-post-slug="${slug}"]`).forEach((node) => {
        node.dataset.status = status;
      });
      document.querySelectorAll(`[data-status-target="${slug}"]`).forEach((node) => {
        node.className = `status-pill ${status}`;
        node.textContent = statusLabel(status);
      });
      document.querySelectorAll(`[data-history-slug="${slug}"]`).forEach((node) => {
        node.dataset.status = status;
      });
    }

    function showMonth(index) {
      const months = [...document.querySelectorAll(".calendar-month")];
      if (!months.length) return;
      activeMonthIndex = Math.max(0, Math.min(index, months.length - 1));
      months.forEach((node, monthIndex) => node.classList.toggle("is-active", monthIndex === activeMonthIndex));
      const label = document.querySelector("[data-month-label]");
      if (label) label.textContent = months[activeMonthIndex].dataset.monthLabel || "";
      document.querySelectorAll("[data-month-prev]").forEach((node) => node.disabled = activeMonthIndex >= months.length - 1);
      document.querySelectorAll("[data-month-next]").forEach((node) => node.disabled = activeMonthIndex <= 0);
    }

    function showReview(slug) {
      activeReviewSlug = slug;
      document.querySelectorAll(".approval-card").forEach((node) => {
        node.classList.toggle("is-active", node.dataset.approvalSlug === slug);
      });
      document.querySelectorAll(".calendar-post").forEach((node) => node.classList.toggle("is-selected", node.dataset.postSlug === slug));
      const empty = document.querySelector("[data-empty-approval]");
      if (empty) empty.classList.toggle("is-active", !slug);
    }

    function nextDraftSlug() {
      const drafts = posts.filter((item) => (item.status || "draft") === "draft");
      if (!drafts.length) return null;
      const dated = drafts.filter((item) => item.date);
      if (!dated.length) return drafts[0].slug;
      const today = new Date().toISOString().slice(0, 10);
      const byDateAsc = dated.slice().sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
      // Surface the nearest upcoming draft to review before it is due.
      // If everything pending is already overdue, surface the most overdue first.
      const upcoming = byDateAsc.find((item) => item.date >= today);
      return (upcoming || byDateAsc[0]).slug;
    }

    function advanceReview() {
      const selected = nextDraftSlug();
      showReview(selected);
    }

    function selectPlatform(slug, platform) {
      const card = document.querySelector(`[data-approval-slug="${slug}"]`);
      if (!card) return;
      card.querySelectorAll(".platform-tab").forEach((node) => {
        node.classList.toggle("is-active", node.dataset.platform === platform);
      });
      card.querySelectorAll(".platform-version").forEach((node) => {
        node.classList.toggle("is-active", node.dataset.platform === platform);
      });
      const copyButton = card.querySelector("[data-copy-platform]");
      if (copyButton) copyButton.dataset.copyPlatform = platform;
    }

    async function copyPlatformText(slug, platform) {
      const post = posts.find((item) => item.slug === slug);
      const text = post && post.copy && post.copy[platform] ? post.copy[platform] : "";
      const message = document.querySelector(`[data-copy-message="${slug}"]`);
      try {
        await navigator.clipboard.writeText(text);
        if (message) message.textContent = `${platform} text copied.`;
      } catch (error) {
        if (message) message.textContent = "Copy failed. Select the text manually from the card.";
      }
    }

    const pexelsState = {};

    async function fetchPexelsCandidates(imageIdea, page) {
      const key = window.CONTENT_RADAR_SUPABASE && window.CONTENT_RADAR_SUPABASE.pexelsKey;
      if (!key) throw new Error("Pexels key not set in supabase-config.js");
      const url = new URL("https://api.pexels.com/v1/search");
      url.searchParams.set("query", imageIdea);
      url.searchParams.set("orientation", "portrait");
      url.searchParams.set("size", "medium");
      url.searchParams.set("per_page", "3");
      url.searchParams.set("page", String(page));
      const resp = await fetch(url.toString(), { headers: { Authorization: key } });
      if (!resp.ok) throw new Error("Pexels API error " + resp.status);
      const data = await resp.json();
      return data.photos || [];
    }

    function showPexelsPicker(slug, photos, card) {
      let picker = card.querySelector(".ci-picker");
      if (!picker) {
        picker = document.createElement("div");
        picker.className = "ci-picker";
        const cardImage = card.querySelector(".card-image");
        if (cardImage) cardImage.appendChild(picker);
      }
      picker.innerHTML = photos.map((photo, i) =>
        `<div class="ci-candidate" data-candidate-index="${i}" ` +
        `data-photo-url="${photo.src.large2x}" data-photo-thumb="${photo.src.medium}" ` +
        `data-post-slug="${slug}">` +
        `<img src="${photo.src.small}" loading="lazy" alt="${photo.photographer}">` +
        `<div class="ci-candidate-credit">${photo.photographer} / Pexels</div>` +
        `</div>`
      ).join("");
    }

    async function regenerateImage(slug) {
      const post = posts.find((item) => item.slug === slug);
      const card = document.querySelector(`[data-approval-slug="${slug}"]`);
      if (!card) return;
      const status = card.querySelector("[data-image-message]");
      const button = card.querySelector("[data-regenerate-image]");
      if (!post || !post.imageIdea) {
        if (status) status.textContent = "No image idea set for this post.";
        return;
      }
      if (button) button.disabled = true;
      if (status) status.textContent = "Searching Pexels...";
      try {
        const state = pexelsState[slug] || { page: 0 };
        state.page = (state.page || 0) + 1;
        pexelsState[slug] = state;
        const photos = await fetchPexelsCandidates(post.imageIdea, state.page);
        if (!photos.length) {
          if (status) status.textContent = "No photos found. Try again or regenerate the draft.";
          if (button) button.disabled = false;
          return;
        }
        showPexelsPicker(slug, photos, card);
        if (status) status.textContent = "Pick a photo below, then approve.";
      } catch (err) {
        if (status) status.textContent = "Could not load photos: " + err.message;
      }
      if (button) button.disabled = false;
    }

    async function selectCandidate(candidateEl) {
      const slug = candidateEl.dataset.postSlug;
      const photoUrl = candidateEl.dataset.photoUrl;
      const photoThumb = candidateEl.dataset.photoThumb;
      const card = document.querySelector(`[data-approval-slug="${slug}"]`);
      if (!card) return;
      const status = card.querySelector("[data-image-message]");
      const mainPhoto = card.querySelector("[data-card-photo]");
      if (mainPhoto) mainPhoto.src = photoThumb;
      candidateEl.closest(".ci-picker").querySelectorAll(".ci-candidate")
        .forEach((c) => c.classList.remove("is-selected"));
      candidateEl.classList.add("is-selected");
      if (radarStatus && radarStatus.saveImage) {
        if (status) status.textContent = "Saving photo choice...";
        radarStatus.saveImage(slug, photoUrl).then((res) => {
          if (!status) return;
          status.textContent = res && res.ok && res.connected !== false
            ? "Photo saved. Approve when ready."
            : "Photo shown here but not synced (review sync not connected).";
        }).catch(() => {
          if (status) status.textContent = "Photo shown but could not be saved.";
        });
      } else if (status) {
        status.textContent = "Photo selected (review sync not connected, will not persist).";
      }
    }

    function syncReasonText(result) {
      if (!result) return "Review sync settings could not be loaded.";
      if (result.error) {
        return "The review database rejected the request (" + result.error +
          "). The post_status table and its access rules may not be set up yet.";
      }
      if (result.reason === "config-missing") {
        return "Set the review database address and key in supabase-config.js.";
      }
      if (result.reason === "sdk-missing") {
        return "The review sync library did not load. Check your network or any " +
          "content/ad blocker, then reload the page.";
      }
      return "Check the review sync settings.";
    }

    function showSyncWarning(detail) {
      let banner = document.querySelector(".sync-warning");
      if (!banner) {
        banner = document.createElement("div");
        banner.className = "sync-warning";
        document.body.prepend(banner);
      }
      banner.textContent =
        "Review sync is not connected, so Approve and Decline will not be saved. " +
        (detail || "Check the review sync settings.");
    }

    async function decidePost(slug, status) {
      const message = document.querySelector(`[data-status-message="${slug}"]`);
      if (message) message.textContent = "Saving decision...";
      const result = radarStatus
        ? await radarStatus.saveStatus(slug, status)
        : { ok: false, error: "Supabase is not configured yet." };
      // Only treat it as saved when the write actually reached Supabase. When
      // unconfigured the wrapper returns ok:true but connected:false / localOnly,
      // which previously showed a false "saved" and silently lost the decision.
      if (result.ok && result.connected !== false && !result.localOnly) {
        applyStatus(slug, status);
        if (message) message.textContent = `${statusLabel(status)} saved.`;
        if (activeReviewSlug === slug) advanceReview();
      } else {
        showSyncWarning(syncReasonText(result));
        if (message) {
          message.textContent =
            "Not saved: review sync is not connected, so this decision will not persist.";
        }
      }
    }

    document.addEventListener("click", (event) => {
      const prev = event.target.closest("[data-month-prev]");
      if (prev) {
        showMonth(activeMonthIndex + 1);
        return;
      }
      const next = event.target.closest("[data-month-next]");
      if (next) {
        showMonth(activeMonthIndex - 1);
        return;
      }
      const openButton = event.target.closest("[data-open-post]");
      if (openButton) {
        showReview(openButton.dataset.openPost);
        return;
      }
      const tab = event.target.closest("[data-platform-tab]");
      if (tab) {
        selectPlatform(tab.dataset.postSlug, tab.dataset.platform);
        return;
      }
      const copy = event.target.closest("[data-copy-platform]");
      if (copy) {
        copyPlatformText(copy.dataset.postSlug, copy.dataset.copyPlatform);
        return;
      }
      const imageButton = event.target.closest("[data-regenerate-image]");
      if (imageButton) {
        regenerateImage(imageButton.dataset.postSlug);
        return;
      }
      const candidate = event.target.closest(".ci-candidate");
      if (candidate) {
        selectCandidate(candidate);
        return;
      }
      const decision = event.target.closest("[data-decision]");
      if (decision) {
        decidePost(decision.dataset.postSlug, decision.dataset.decision);
      }
    });

    async function hydrateStatuses() {
      if (!radarStatus) {
        showSyncWarning(syncReasonText(null));
        return;
      }
      const result = await radarStatus.loadStatuses(posts.map((post) => post.slug));
      if (!result.ok) {
        console.warn(result.error || "Status sync is not configured.");
        showSyncWarning(syncReasonText(result));
        return;
      }
      if (result.connected === false) {
        // Unconfigured: saved decisions cannot be loaded back, so surface it now
        // rather than silently showing every post as a fresh draft.
        showSyncWarning(syncReasonText(result));
        return;
      }
      Object.entries(result.statuses).forEach(([slug, status]) => applyStatus(slug, status));
      advanceReview();
    }

    function applyImage(slug, url) {
      const card = document.querySelector(`[data-approval-slug="${slug}"]`);
      if (!card) return;
      const photo = card.querySelector("[data-card-photo]");
      if (photo && url) photo.src = url;
    }

    async function hydrateImages() {
      if (!radarStatus || !radarStatus.loadImages) return;
      const result = await radarStatus.loadImages(posts.map((post) => post.slug));
      if (!result || !result.ok || result.connected === false) return;
      Object.entries(result.images || {}).forEach(([slug, url]) => applyImage(slug, url));
    }

    showMonth(activeMonthIndex);
    advanceReview();
    hydrateStatuses();
    hydrateImages();
  </script>
</body>
</html>
"""


def parse_scalar(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        try:
            return ast.literal_eval(value)
        except Exception:
            return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    frontmatter_lines: list[str] = []
    body_start = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            body_start = idx + 1
            break
        frontmatter_lines.append(lines[idx])

    if body_start is None:
        return {}, text

    data: dict = {}
    current_key = None
    current_mode = None
    current_item = None

    for raw_line in frontmatter_lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if re.match(r"^[A-Za-z0-9_-]+:\s*", stripped) and not line.startswith(" "):
            key, _, remainder = stripped.partition(":")
            remainder = remainder.strip()
            if remainder:
                data[key] = parse_scalar(remainder)
                current_key = None
                current_mode = None
                current_item = None
            else:
                current_key = key
                current_item = None
                if key == "platforms":
                    data[key] = []
                    current_mode = "scalar_list"
                elif key == "sources":
                    data[key] = []
                    current_mode = "dict_list"
                else:
                    data[key] = None
                    current_mode = "pending"
            continue

        if current_mode == "scalar_list" and stripped.startswith("- "):
            data[current_key].append(parse_scalar(stripped[2:]))
            continue

        if current_mode == "dict_list":
            if stripped.startswith("- "):
                item_text = stripped[2:].strip()
                current_item = {}
                if item_text and ":" in item_text:
                    item_key, item_value = item_text.split(":", 1)
                    current_item[item_key.strip()] = parse_scalar(item_value.strip())
                elif item_text:
                    current_item["value"] = parse_scalar(item_text)
                data[current_key].append(current_item)
                continue
            if current_item is not None and ":" in stripped:
                item_key, item_value = stripped.split(":", 1)
                current_item[item_key.strip()] = parse_scalar(item_value.strip())
                continue

        if current_mode == "pending" and current_key and ":" in stripped:
            item_key, item_value = stripped.split(":", 1)
            if item_key.strip() == current_key:
                data[current_key] = parse_scalar(item_value.strip())
                current_mode = None
                current_key = None

    body = "\n".join(lines[body_start:])
    return data, body


def parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = None
    buffer: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = line[3:].strip().lower()
            buffer = []
        elif current is not None:
            buffer.append(line)

    if current is not None:
        sections[current] = "\n".join(buffer).strip()

    return sections


def split_hashtags(text: str) -> tuple[list[str], str]:
    hashtags: list[str] = []
    content_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and all(part.startswith("#") for part in stripped.split()):
            hashtags.extend(stripped.split())
            continue
        content_lines.append(line)
    return hashtags, "\n".join(content_lines).strip()


def render_paragraphs(text: str) -> str:
    if not text.strip():
        return ""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]
    return "".join(
        f"<p>{html.escape(paragraph).replace(chr(10), '<br>')}</p>"
        for paragraph in paragraphs
    )


def render_hashtags(tags: list[str]) -> str:
    if not tags:
        return ""
    return "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in tags)


def render_sources(sources: list[dict]) -> str:
    if not sources:
        return ""
    links = []
    for source in sources:
        title = html.escape(str(source.get("title", "Source")))
        url = html.escape(str(source.get("url", "")), quote=True)
        if url:
            links.append(f'<a href="{url}" target="_blank" rel="noreferrer">"{title}"</a>')
        else:
            links.append(f'"{title}"')
    return '<div class="source-list">' + " · ".join(links) + "</div>"


FB_AVATAR = "assets/macfire-logo.png"
X_AVATAR = "assets/macfire-logo.png"
LI_AVATAR = "assets/macfire-van.jpg"

# Inline SVGs sized via CSS
SVG_GLOBE = '<svg viewBox="0 0 16 16"><path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zm0 14.5A6.5 6.5 0 1 1 14.5 8 6.5 6.5 0 0 1 8 14.5zM4 8a4 4 0 1 1 8 0 4 4 0 0 1-8 0z"/></svg>'
SVG_DOTS = '<svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>'
SVG_CLOSE = '<svg viewBox="0 0 24 24"><path d="M18.3 5.71 12 12l6.3 6.29-1.41 1.42L10.59 13.41 4.29 19.71 2.88 18.3 9.17 12 2.88 5.71 4.29 4.29l6.3 6.3 6.29-6.3z"/></svg>'
SVG_FB_LIKE = '<svg viewBox="0 0 24 24"><path d="M2 8.74h3v12H2v-12zm20.07 1.81a2.42 2.42 0 0 0-1.87-.81H14.7l.6-3.06c.13-.66-.07-1.34-.55-1.81-.83-.83-2.27-.82-3.09.01l-3.6 3.6-.06.07v11.7l1.18 1.18a2.4 2.4 0 0 0 1.7.7h7.94c.97 0 1.81-.62 2.13-1.55l1.92-7.94c.18-.74.01-1.51-.46-2.07z"/></svg>'
SVG_FB_COMMENT = '<svg viewBox="0 0 24 24"><path d="M12 2C6.49 2 2 6.04 2 11c0 2.27.94 4.34 2.5 5.93V21l4.06-2.23c1.07.32 2.22.49 3.44.49 5.51 0 10-4.04 10-9s-4.49-9-10-9z" fill="none" stroke="currentColor" stroke-width="2"/></svg>'
SVG_FB_SHARE = '<svg viewBox="0 0 24 24"><path d="M14 9V5l7 7-7 7v-4.1c-5 0-8.5 1.6-11 5.1 1-5 4-10 11-11z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>'
SVG_LI_LIKE = '<svg viewBox="0 0 24 24"><path d="M19.46 11l-3.91-3.91a7 7 0 0 1-1.69-2.74l-.49-1.47A2.76 2.76 0 0 0 10.76 1 2.75 2.75 0 0 0 8 3.74v1.12a9.19 9.19 0 0 0 .46 2.85L8.89 9H4.12A2.12 2.12 0 0 0 2 11.12a2.16 2.16 0 0 0 .92 1.76A2.11 2.11 0 0 0 2 14.62a2.14 2.14 0 0 0 1.28 2 2 2 0 0 0-.28 1A2.12 2.12 0 0 0 5.12 20a2 2 0 0 0-.12.63A2.34 2.34 0 0 0 7.34 23h7.27A8.31 8.31 0 0 0 22 14.69V13a2 2 0 0 0-2.54-2z"/></svg>'
SVG_LI_COMMENT = '<svg viewBox="0 0 24 24"><path d="M7 9h10v1H7zm0 4h7v-1H7zm16-2a6.78 6.78 0 0 1-2.84 5.61L12 22v-4H8A7 7 0 0 1 8 4h8a7 7 0 0 1 7 7zm-2 0a5 5 0 0 0-5-5H8a5 5 0 0 0 0 10h6v2.28L19 15a4.79 4.79 0 0 0 2-4z"/></svg>'
SVG_LI_REPOST = '<svg viewBox="0 0 24 24"><path d="m23 12-4.61 4.61L17 15.06l1.94-2.06H5a3 3 0 0 0-3 3v3H0v-3a5 5 0 0 1 5-5h13.94L17 8.94l1.39-1.55zM3.06 9 5 6.94l-1.39-1.55L1 8 5.61 12.61 7 11.06 5.06 9z"/></svg>'
SVG_LI_SEND = '<svg viewBox="0 0 24 24"><path d="M21 3 0 10l7.66 4.26L16 8l-6.26 8.34L14 24z"/></svg>'
SVG_X_REPLY = '<svg viewBox="0 0 24 24"><path d="M21 12a8.5 8.5 0 0 1-8.5 8.5H7l-4 2v-6.5A8.5 8.5 0 1 1 21 12z"/></svg>'
SVG_X_REPOST = '<svg viewBox="0 0 24 24"><path d="M17 2l4 4-4 4"/><path d="M3 11V8a2 2 0 0 1 2-2h16"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v3a2 2 0 0 1-2 2H3"/></svg>'
SVG_X_LIKE = '<svg viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 1 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>'
SVG_X_VIEWS = '<svg viewBox="0 0 24 24"><path d="M4 19V9"/><path d="M10 19V5"/><path d="M16 19v-8"/><path d="M22 19V3"/></svg>'
SVG_X_SHARE = '<svg viewBox="0 0 24 24"><path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M5 16v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3"/></svg>'


def render_paragraphs_plain(text: str, css_class: str) -> str:
    if not text.strip():
        return ""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "".join(
        f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs
    )


def render_li_hashtags(tags: list[str]) -> str:
    if not tags:
        return ""
    spans = "".join(f"<span>{html.escape(t)}</span>" for t in tags)
    return f'<div class="li-hashtags">{spans}</div>'


def inline_fb_body_with_tags(text: str, hashtags: list[str]) -> str:
    body = render_paragraphs_plain(text, "fb-body")
    if hashtags:
        tags_html = " ".join(
            f'<span style="color:#1877f2">{html.escape(t)}</span>' for t in hashtags
        )
        body += f"<p>{tags_html}</p>"
    return body


def inline_x_body_with_tags(text: str, hashtags: list[str]) -> str:
    body = render_paragraphs_plain(text, "x-body")
    if hashtags:
        tags_html = " ".join(
            f'<span style="color:#1d9bf0">{html.escape(t)}</span>' for t in hashtags
        )
        body += f"<p>{tags_html}</p>"
    return body


def character_count(text: str) -> int:
    return len(re.sub(r"\s+", " ", text).strip())


def render_sources_note(sources: list[dict]) -> str:
    if not sources:
        return ""
    links = []
    for source in sources:
        title = html.escape(str(source.get("title", "Source")))
        url = html.escape(str(source.get("url", "")), quote=True)
        published = format_source_published(source)
        suffix = f" ({html.escape(published)})" if published else ""
        if url:
            links.append(f'<a href="{url}" target="_blank" rel="noreferrer">{title}</a>{suffix}')
        else:
            links.append(title + suffix)
    return '<div class="sources-note">Sources referenced: ' + " · ".join(links) + "</div>"


def render_inline_source_paragraph(sources: list[dict], color: str) -> str:
    if not sources:
        return ""
    links = []
    for source in sources:
        title = html.escape(str(source.get("title", "Source")))
        url = html.escape(str(source.get("url", "")), quote=True)
        if url:
            links.append(
                f'<a href="{url}" target="_blank" rel="noreferrer" '
                f'style="color:{color};text-decoration:none">{title}</a>'
            )
        else:
            links.append(title)
    label = "Source" if len(links) == 1 else "Sources"
    return f'<p>{label}: ' + " · ".join(links) + "</p>"


def render_facebook_card(post: dict) -> str:
    sections = post["sections"]
    text = sections.get("facebook", "")
    hashtags, copy_text = split_hashtags(text)
    body_html = inline_fb_body_with_tags(copy_text, hashtags)
    body_html += render_inline_source_paragraph(post["meta"].get("sources", []), "#1877f2")
    return f"""
      <div class=\"platform-card\">
        <div class=\"platform-label fb\">Facebook · MacFire Ltd page</div>
        <article class=\"fb-post\">
          <div class=\"fb-header\">
            <div class=\"fb-avatar\" style=\"background-image:url('{FB_AVATAR}')\"></div>
            <div class=\"fb-meta\">
              <div class=\"fb-name\">MacFire Ltd</div>
              <div class=\"fb-sub\"><span>2 h</span> · {SVG_GLOBE}</div>
            </div>
          </div>
          <div class=\"fb-body\">{body_html}</div>
        </article>
      </div>
    """


def render_x_card(post: dict) -> str:
    sections = post["sections"]
    text = sections.get("x", "")
    hashtags, copy_text = split_hashtags(text)
    body_html = inline_x_body_with_tags(copy_text, hashtags)
    body_html += render_inline_source_paragraph(post["meta"].get("sources", []), "#1d9bf0")
    count = character_count(text)
    count_state = "Ready for one X post" if count <= 280 else "Review length before posting"
    return f"""
      <div class=\"platform-card\">
        <div class=\"platform-label x\">X · @MacFireLtd</div>
        <article class=\"x-post\">
          <div class=\"x-header\">
            <div class=\"x-avatar\" style=\"background-image:url('{X_AVATAR}')\"></div>
            <div class=\"x-meta\">
              <div class=\"x-name-line\">
                <span class=\"x-name\">MacFire Ltd</span>
                <span class=\"x-handle\">@MacFireLtd · 2h</span>
              </div>
            </div>
          </div>
          <div class=\"x-body\">{body_html}</div>
          <div class=\"x-count\">{count} characters · {count_state}</div>
        </article>
      </div>
    """


def render_linkedin_card(post: dict) -> str:
    sections = post["sections"]
    text = sections.get("linkedin", "")
    hashtags, copy_text = split_hashtags(text)
    body_html = render_paragraphs_plain(copy_text, "li-body")
    body_html += render_inline_source_paragraph(post["meta"].get("sources", []), "#0a66c2")
    tags_html = render_li_hashtags(hashtags)
    return f"""
      <div class=\"platform-card\">
        <div class=\"platform-label li\">LinkedIn · MacFire Ltd Fire Protection page</div>
        <article class=\"li-post\">
          <div class=\"li-header\">
            <div class=\"li-avatar\" style=\"background-image:url('{LI_AVATAR}')\"></div>
            <div class=\"li-meta\">
              <div class=\"li-name\">MacFire Ltd Fire Protection</div>
              <div class=\"li-tag\">Fire Protection Services at MacFire Ltd</div>
              <div class=\"li-sub\"><span>2 h</span> · {SVG_GLOBE}</div>
            </div>
          </div>
          <div class=\"li-body\">{body_html}</div>
          {tags_html}
        </article>
      </div>
    """


def post_slug(post: dict) -> str:
    return post["path"].stem


def post_status(post: dict) -> str:
    status = str(post["meta"].get("status", "draft")).strip().lower()
    return status if status in {"draft", "approved", "declined", "published"} else "draft"


def post_card(post: dict) -> dict:
    """Parse the post's `card:` block via YAML.

    The lightweight frontmatter parser used elsewhere in this file does not
    descend into nested mappings, so card.photo / card.headline / card.image_idea
    come back empty without this. Read them properly from the source file.
    """
    try:
        text = post["path"].read_text(encoding="utf-8")
        if not text.startswith("---"):
            return {}
        _, fm, _ = text.split("---", 2)
        data = yaml.safe_load(fm) or {}
        card = data.get("card")
        return card if isinstance(card, dict) else {}
    except Exception:
        return {}


MACFIRE_LOGO_SVG = """<svg class="__CLS__" viewBox="0 0 270 100" xmlns="http://www.w3.org/2000/svg" aria-label="MacFire Ltd, Fire Protection Company">
<rect width="270" height="100" fill="#1A1F3C"/>
<rect x="2" y="69" width="266" height="29" fill="#ffffff"/>
<text x="7" y="57" font-family="Impact,'Arial Black',sans-serif" font-size="46" fill="#ffffff" textLength="107" lengthAdjust="spacingAndGlyphs">Mac</text>
<text x="119" y="57" font-family="Impact,'Arial Black',sans-serif" font-size="46" fill="#ffffff" textLength="92" lengthAdjust="spacingAndGlyphs">Fire</text>
<text x="213" y="57" font-family="Impact,'Arial Black',sans-serif" font-size="34" fill="#ffffff" textLength="53" lengthAdjust="spacingAndGlyphs">Ltd</text>
<text x="135" y="83" text-anchor="middle" dominant-baseline="central" font-family="Arial,Helvetica,sans-serif" font-weight="bold" font-size="17" fill="#C31E1F" letter-spacing="1.5">Fire Protection Company</text>
</svg>"""


def macfire_logo_svg(css_class: str) -> str:
    return MACFIRE_LOGO_SVG.replace("__CLS__", css_class)


def _highlight_headline(text: str) -> str:
    """Escape HTML, then turn *asterisk* spans into red highlight spans."""
    parts = re.split(r"\*(.+?)\*", text or "")
    out = []
    for i, part in enumerate(parts):
        esc = html.escape(part)
        out.append(f'<span class="hl">{esc}</span>' if i % 2 else esc)
    return "".join(out)


def render_card_image(post: dict) -> str:
    """Live image for the approval view: a photo the reviewer can regenerate in
    place, with the brand overlay drawn on top for sell posts. The page lives in
    preview/, so the repo-root content/images path is reached with a leading ../.

    Sell posts composite the brand overlay over the text-free background photo so
    a regenerated photo keeps its branding without re-rendering on a server.
    """
    meta = post["meta"]
    card = post_card(post)
    slug = html.escape(post_slug(post), quote=True)
    intent = str(meta.get("intent", "")).strip().lower()

    has_photo = bool(card.get("photo"))
    # Sell posts overlay branding only when we have the raw background photo
    # (otherwise the fallback image already has text baked in).
    overlay_ok = intent == "sell" and has_photo and bool(card.get("headline"))
    photo_rel = card.get("photo") if has_photo else meta.get("image", "")
    if not photo_rel:
        return ""
    photo_src = html.escape("../" + str(photo_rel).lstrip("/"), quote=True)

    overlay = ""
    if overlay_ok:
        overlay = (
            '<div class="ci-overlay"><div class="ci-scrim"></div>'
            '<div class="ci-frame"><div class="ci-rule"></div>'
            f'<div class="ci-headline">{_highlight_headline(card.get("headline", ""))}</div>'
            '<div class="ci-footer">'
            + macfire_logo_svg("ci-logo") +
            '<span class="ci-phone">0141 881 5455</span>'
            '</div></div></div>'
        )

    return (
        f'<div class="card-image">'
        f'<div class="ci-stage">'
        f'<img class="ci-photo" data-card-photo src="{photo_src}" alt="Post image" loading="lazy">'
        f'{overlay}'
        f'</div>'
        f'<div class="image-review-actions">'
        f'<button class="image-regen-btn" type="button" data-regenerate-image data-post-slug="{slug}">'
        f'Find images</button>'
        f'<span class="small-meta" data-image-message="{slug}"></span>'
        f'</div>'
        f'</div>'
    )


def first_source_label(post: dict) -> str:
    sources = post["meta"].get("sources", [])
    if not sources:
        return "No source listed"
    return str(sources[0].get("title", "Source"))


def parse_iso_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def format_date_long(day: date) -> str:
    return day.strftime("%-d %B %Y")


def format_source_published(source: dict) -> str:
    published = parse_iso_date(source.get("published") or source.get("published_at"))
    return f"published {format_date_long(published)}" if published else ""


def freshness_info(post: dict) -> dict[str, str]:
    published_dates = [
        parsed
        for source in post["meta"].get("sources", [])
        for parsed in [parse_iso_date(source.get("published") or source.get("published_at"))]
        if parsed
    ]
    if not published_dates:
        return {"status": "unknown", "label": "Source date unknown"}

    newest = max(published_dates)
    age_days = (date.today() - newest).days
    if age_days < 0:
        return {"status": "fresh", "label": f"Source publishes {format_date_long(newest)}"}
    if age_days <= 90:
        status = "fresh"
        prefix = "Fresh source"
    elif age_days <= 180:
        status = "ageing"
        prefix = "Ageing source"
    else:
        status = "stale"
        prefix = "Stale source"
    return {
        "status": status,
        "label": f"{prefix}: {age_days} days old",
    }


def render_freshness_pill(post: dict) -> str:
    info = freshness_info(post)
    status = html.escape(info["status"], quote=True)
    label = html.escape(info["label"])
    return f'<span class="freshness-pill {status}">{label}</span>'


def platform_text(post: dict, platform: str) -> str:
    return post["sections"].get(platform, "").strip()


def copy_text_for_platform(post: dict, platform: str) -> str:
    text = platform_text(post, platform)
    source_lines = []
    for source in post["meta"].get("sources", []):
        title = str(source.get("title", "Source")).strip()
        url = str(source.get("url", "")).strip()
        if title and url:
            source_lines.append(f"Source: {title} - {url}")
        elif title:
            source_lines.append(f"Source: {title}")
    if source_lines:
        return text + "\n\n" + "\n".join(source_lines)
    return text


def canonical_platform(post: dict) -> str:
    if platform_text(post, "facebook"):
        return "facebook"
    if platform_text(post, "linkedin"):
        return "linkedin"
    if platform_text(post, "x"):
        return "x"
    return "facebook"


def render_platform_card(post: dict, platform: str) -> str:
    if platform == "facebook":
        return render_facebook_card(post)
    if platform == "linkedin":
        return render_linkedin_card(post)
    return render_x_card(post)


def render_review_card(post: dict) -> str:
    meta = post["meta"]
    slug = html.escape(post_slug(post), quote=True)
    status = post_status(post)
    title = html.escape(meta.get("title", post["path"].stem))
    date = html.escape(meta.get("date", ""))
    source = html.escape(first_source_label(post))
    freshness = render_freshness_pill(post)
    platform = canonical_platform(post)
    platform_name = {"facebook": "Facebook", "linkedin": "LinkedIn", "x": "X"}[platform]
    return f"""
      <article class=\"review-card\" data-post-slug=\"{slug}\" data-status=\"{status}\">
        <div class=\"review-card-head\">
          <div>
            <h3>{title}</h3>
            <div class=\"review-card-meta\">
              <span>{date}</span>
              <span>{source}</span>
              {freshness}
              <span>Collapsed preview: {platform_name}</span>
            </div>
          </div>
          <span class=\"status-pill {status}\" data-status-target=\"{slug}\">{status.title()}</span>
        </div>
        <div class=\"canonical-preview\">
          {render_platform_card(post, platform)}
        </div>
        <button class=\"open-detail-btn\" type=\"button\" data-open-post=\"{slug}\">Open review</button>
      </article>
    """


def render_calendar(posts: list[dict]) -> str:
    from calendar import monthrange
    from datetime import timedelta

    dated_posts = []
    for post in posts:
        try:
            year, month, day = [int(part) for part in str(post["meta"].get("date", "")).split("-")]
            dated_posts.append((date(year, month, day), post))
        except Exception:
            continue

    today = date.today()
    current_month = today.replace(day=1)

    def add_months(day: date, offset: int) -> date:
        month_number = day.month - 1 + offset
        return date(day.year + month_number // 12, month_number % 12 + 1, 1)

    year_end = date(today.year, 12, 1)
    month_set = {
        add_months(current_month, offset)
        for offset in range(-12, 13)
        if add_months(current_month, offset) <= year_end
    }
    month_set.update(
        day.replace(day=1)
        for day, _post in dated_posts
        if day.replace(day=1) <= year_end
    )
    month_dates = sorted(month_set, reverse=True)
    active_index = month_dates.index(current_month) if current_month in month_dates else 0

    posts_by_day: dict[date, list[dict]] = {}
    for day, post in dated_posts:
        posts_by_day.setdefault(day, []).append(post)

    rendered_months = []
    for month_index, month_date in enumerate(month_dates):
        first_weekday, _days_in_month = monthrange(month_date.year, month_date.month)
        start = month_date - timedelta(days=first_weekday)
        cells = []
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cells.extend(f'<div class="weekday">{day}</div>' for day in weekdays)
        for offset in range(42):
            current = start + timedelta(days=offset)
            muted = " is-muted" if current.month != month_date.month else ""
            buttons = []
            for post in posts_by_day.get(current, []):
                slug = html.escape(post_slug(post), quote=True)
                title = html.escape(post["meta"].get("title", post["path"].stem))
                status = post_status(post)
                buttons.append(
                    f'<button class="calendar-post" type="button" data-open-post="{slug}" '
                    f'data-post-slug="{slug}" data-status="{status}">'
                    f'<span class="calendar-post-title">{title}</span></button>'
                )
            cells.append(
                f'<div class="calendar-day{muted}">'
                f'<div class="day-number">{current.day}</div>'
                + "".join(buttons)
                + "</div>"
            )

        month_label = month_date.strftime("%B %Y")
        rendered_months.append(f"""
        <div class=\"calendar-month{' is-active' if month_index == active_index else ''}\" data-month-label=\"{html.escape(month_label, quote=True)}\">
          <div class=\"calendar-grid\">
            {"".join(cells)}
          </div>
        </div>
        """)
    first_label = month_dates[active_index].strftime("%B %Y")
    return f"""
    <section class=\"calendar-shell\" data-active-month-index=\"{active_index}\">
      <div class=\"calendar-head\">
        <div>
          <h2 data-month-label>{html.escape(first_label)}</h2>
        </div>
        <div class=\"month-controls\">
          <button class=\"month-btn\" type=\"button\" data-month-prev aria-label=\"Previous month\">&lt;</button>
          <button class=\"month-btn\" type=\"button\" data-month-next aria-label=\"Next month\">&gt;</button>
        </div>
      </div>
      <div class=\"status-legend\" aria-label=\"Status legend\">
        <span class=\"legend-item\"><span class=\"status-dot draft\"></span>Draft</span>
        <span class=\"legend-item\"><span class=\"status-dot approved\"></span>Approved</span>
        <span class=\"legend-item\"><span class=\"status-dot published\"></span>Published</span>
        <span class=\"legend-item\"><span class=\"status-dot declined\"></span>Declined</span>
      </div>
      {"".join(rendered_months)}
    </section>
    """


def render_approval_card(post: dict) -> str:
    meta = post["meta"]
    sections = post["sections"]
    slug = html.escape(post_slug(post), quote=True)
    status = post_status(post)
    title = html.escape(meta.get("title", post["path"].stem))
    angle_html = render_paragraphs(sections.get("angle", "").strip())
    notes_html = render_paragraphs(sections.get("notes", "").strip())
    date = html.escape(meta.get("date", ""))
    source = html.escape(first_source_label(post))
    sources_note = render_sources_note(meta.get("sources", []))
    freshness = render_freshness_pill(post)

    return f"""
      <article class=\"approval-card\" data-approval-slug=\"{slug}\" data-post-slug=\"{slug}\" data-status=\"{status}\">
        <div class=\"approval-card-head\">
          <div>
            <h3>{title}</h3>
            <div class=\"review-card-meta\">
              <span>{date}</span>
              <span>{source}</span>
              {freshness}
            </div>
          </div>
          <span class=\"status-pill {status}\" data-status-target=\"{slug}\">{status.title()}</span>
        </div>
        {render_card_image(post)}
        <div class=\"approval-actions\">
          <div class=\"platform-toolbar\">
            <div class=\"platform-tabs\">
              <button class=\"platform-tab is-active\" type=\"button\" data-platform-tab data-post-slug=\"{slug}\" data-platform=\"facebook\">Facebook</button>
              <button class=\"platform-tab\" type=\"button\" data-platform-tab data-post-slug=\"{slug}\" data-platform=\"linkedin\">LinkedIn</button>
              <button class=\"platform-tab\" type=\"button\" data-platform-tab data-post-slug=\"{slug}\" data-platform=\"x\">X</button>
            </div>
            <button class=\"copy-btn\" type=\"button\" data-post-slug=\"{slug}\" data-copy-platform=\"facebook\">Copy text</button>
          </div>
          <div class=\"small-meta\" data-copy-message=\"{slug}\"></div>
        </div>
        <div>
          <div class=\"platform-version is-active\" data-platform=\"facebook\">{render_facebook_card(post)}</div>
          <div class=\"platform-version\" data-platform=\"linkedin\">{render_linkedin_card(post)}</div>
          <div class=\"platform-version\" data-platform=\"x\">{render_x_card(post)}</div>
        </div>
        <div class=\"detail-actions\">
          <button class=\"decision-btn approve\" type=\"button\" data-post-slug=\"{slug}\" data-decision=\"approved\">Approve</button>
          <button class=\"decision-btn decline\" type=\"button\" data-post-slug=\"{slug}\" data-decision=\"declined\">Decline</button>
        </div>
        <div class=\"status-message\" data-status-message=\"{slug}\"></div>
        {sources_note}
        <div class=\"review-context\">
          <div class=\"review-context-row\">
            <strong>Angle</strong>
            <div class=\"detail-text\">{angle_html or "<p>No angle supplied.</p>"}</div>
          </div>
          <div class=\"review-context-row\">
            <strong>Notes</strong>
            <div class=\"detail-text\">{notes_html or "<p>No notes supplied.</p>"}</div>
          </div>
        </div>
      </article>
    """


def render_history_card(post: dict) -> str:
    meta = post["meta"]
    slug = html.escape(post_slug(post), quote=True)
    status = post_status(post)
    title = html.escape(meta.get("title", post["path"].stem))
    date = html.escape(meta.get("date", ""))
    source = html.escape(first_source_label(post))
    return f"""
      <button class=\"history-card\" type=\"button\" data-open-post=\"{slug}\" data-history-slug=\"{slug}\" data-post-slug=\"{slug}\" data-status=\"{status}\">
        <div class=\"review-card-head\">
          <h3>{title}</h3>
          <span class=\"status-pill {status}\" data-status-target=\"{slug}\">{status.title()}</span>
        </div>
        <div class=\"review-card-meta\">
          <span>{date}</span>
          <span>{source}</span>
        </div>
      </button>
    """


def render_sections(posts: list[dict]) -> str:
    approvals_html = "\n".join(render_approval_card(post) for post in posts)
    history_html = "\n".join(render_history_card(post) for post in posts)
    return f"""
    <div class=\"review-desk\">
      {render_calendar(posts)}
      <section class=\"approval-shell\">
        <div class=\"approval-head\">
          <div>
            <h2>Next approval</h2>
          </div>
        </div>
        <div class=\"empty-approval\" data-empty-approval>All drafts have been reviewed.</div>
{approvals_html}
      </section>
    </div>
    <section class=\"history-shell\">
      <div class=\"history-head\">
        <div>
          <h2>Reviewed posts</h2>
          <div class=\"small-meta\">Approved, declined, and published posts stay available from the calendar.</div>
        </div>
      </div>
      <div class=\"history-grid\">
{history_html}
      </div>
    </section>
    """


def collect_posts() -> list[dict]:
    cutoff = date(date.today().year, 12, 31)
    posts: list[dict] = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        post_date = parse_iso_date(meta.get("date", ""))
        if post_date and post_date > cutoff:
            continue
        posts.append(
            {
                "path": path,
                "meta": meta,
                "sections": parse_sections(body),
            }
        )
    return sorted(
        posts,
        key=lambda post: (
            str(post["meta"].get("date", "")),
            post["path"].name,
        ),
        reverse=True,
    )


def render_page(posts: list[dict]) -> str:
    sections_html = render_sections(posts)
    posts_json = json.dumps(
        [
            {
                "slug": post_slug(post),
                "title": post["meta"].get("title", post["path"].stem),
                "date": post["meta"].get("date", ""),
                "status": post_status(post),
                "imageIdea": post_card(post).get("image_idea", ""),
                "copy": {
                    "facebook": copy_text_for_platform(post, "facebook"),
                    "linkedin": copy_text_for_platform(post, "linkedin"),
                    "x": copy_text_for_platform(post, "x"),
                },
            }
            for post in posts
        ],
        ensure_ascii=False,
    )
    html_text = HTML_TEMPLATE.replace("__SECTIONS__", sections_html)
    html_text = html_text.replace("__POST_COUNT__", str(len(posts)))
    html_text = html_text.replace("__CUTOFF_YEAR__", str(date.today().year))
    html_text = html_text.replace("__POSTS_JSON__", posts_json)
    return "\n".join(line.rstrip() for line in html_text.splitlines()) + "\n"


def build(skip_link_check: bool = False) -> int:
    if not skip_link_check:
        import validate_links

        print("Validating links in draft posts...")
        rc = validate_links.validate()
        if rc != 0:
            print("Build aborted: fix the broken links above or rerun with --skip-link-check.")
            return rc
    posts = collect_posts()
    OUTPUT_PATH.write_text(render_page(posts), encoding="utf-8")
    print(f"Built preview for {len(posts)} post(s) -> {OUTPUT_PATH}")
    return 0


def snapshot_posts() -> dict[str, tuple[int, int]]:
    snap: dict[str, tuple[int, int]] = {}
    for path in sorted(POSTS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        stat = path.stat()
        snap[str(path)] = (stat.st_mtime_ns, stat.st_size)
    return snap


def watch() -> int:
    print("Watching content/posts for changes. Press Ctrl+C to stop.")
    last_snapshot = None
    try:
        while True:
            current_snapshot = snapshot_posts()
            if current_snapshot != last_snapshot:
                build()
                last_snapshot = current_snapshot
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopped watching.")
        return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true", help="Rebuild when markdown drafts change.")
    parser.add_argument("--skip-link-check", action="store_true", help="Skip URL reachability check before building.")
    args = parser.parse_args(argv)

    if args.watch:
        return watch()

    return build(skip_link_check=args.skip_link_check)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
