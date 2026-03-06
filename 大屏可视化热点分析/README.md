# 热点数据抓取与情感分析大屏（B站/特定网站）

这个项目提供一条可复用的数据链路：

1. 抓取热点数据（默认 B 站热点榜）
2. 抓取评论并做中文清洗
3. 使用 SnowNLP 进行情感分析
4. 使用结巴分词抽取高频关键词
5. 用 Streamlit + ECharts 展示分析大屏

适合复试项目展示，兼顾“数据挖掘 + 可视化表达”。

## 技术栈

- Python
- BeautifulSoup / Requests（抓取）
- Pandas（清洗与聚合）
- SnowNLP + 结巴分词（情感分析与关键词提取）
- Streamlit + ECharts（可视化大屏）

## 目录结构

```text
.
├─ app/
│  └─ dashboard.py
├─ data/
│  ├─ raw/
│  └─ processed/
├─ src/
│  ├─ config.py
│  ├─ scraper.py
│  ├─ processing.py
│  └─ pipeline.py
├─ requirements.txt
└─ README.md
```

## 1) 安装依赖

```bash
pip install -r requirements.txt
```

## 2) 运行数据管道

### 模式 A：B 站热点（默认）

```bash
python -m src.pipeline --mode bilibili --video-limit 30 --comment-pages 2
```

常用参数：

- `--video-limit`：抓取热点视频数量
- `--comment-pages`：每个视频抓取评论页数
- `--page-size`：每页评论条数（默认 20）

### 模式 B：特定网站热点（自定义选择器）

```bash
python -m src.pipeline --mode website --url "https://example.com" --item-selector ".hot-item" --title-selector "a"
```

- `--item-selector`：热点条目 CSS 选择器
- `--title-selector`：从条目中提取标题的子选择器（可选）

## 3) 启动可视化大屏

```bash
streamlit run app/dashboard.py
```

### Windows 一键启动（推荐）

在 PowerShell 中执行：

```powershell
./run_dashboard.ps1
```

默认行为：先抓取并分析数据，再启动大屏。

常用参数示例：

```powershell
# 小规模快速跑
./run_dashboard.ps1 -VideoLimit 10 -CommentPages 1

# 仅启动大屏（不重新抓取）
./run_dashboard.ps1 -SkipPipeline
```

## 4) 输出文件说明

- `data/raw/bilibili_hot_raw.json`：B 站原始抓取数据
- `data/raw/website_hot_raw.json`：自定义网站原始热点
- `data/processed/hot_videos_sentiment.csv`：热点级别聚合结果
- `data/processed/video_comments_sentiment.csv`：评论级别情感结果
- `data/processed/hot_keywords.csv`：关键词与权重
- `data/processed/dashboard_summary.json`：大屏概览指标

## 5) 注意事项

- 建议仅用于学习与学术展示，遵守目标网站 robots 协议与平台规则。
- 如果网络环境导致抓取失败，可降低 `--video-limit` 与 `--comment-pages` 重试。
