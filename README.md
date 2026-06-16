---
title: GRC Grid Reversal Web
emoji: 🎞️
colorFrom: green
colorTo: gray
sdk: docker
pinned: false
license: mit
short_description: Grid reversal web app.
---

# GRC Grid Reversal Web

服务端网页版，基于现有 `Grid_Reversal_Enc.py` 和 `Grid_Reversal_Dec.py` 逻辑实现。

## 功能

- 上传图片、GIF、视频
- 网页端选择编码加扰或解码还原
- 服务端完成处理并返回预览和下载

## 免费上线

优先部署到 Hugging Face Spaces：

1. 新建一个 `Docker` 类型 Space
2. 连接这个仓库
3. 等待自动构建

## 本地运行

```bash
pip install -r requirements.txt
python app.py
```

## Docker

```bash
docker build -t grc-grid-reversal-web .
docker run -p 7860:7860 grc-grid-reversal-web
```
