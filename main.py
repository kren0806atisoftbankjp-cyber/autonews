import os
import requests
import feedparser
from openai import OpenAI

# ============================
#        API KEYS
# ============================
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Messaging API
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

client = OpenAI(api_key=OPENAI_API_KEY)


# ============================
#     国内ニュース（Yahoo）
# ============================
def get_japan_rss():
    feeds = [
        "https://news.yahoo.co.jp/rss/categories/business.xml",
        "https://news.yahoo.co.jp/rss/topics/business.xml",
        "https://news.yahoo.co.jp/rss/categories/politics.xml",
    ]

    articles = []
    seen = set()

    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            desc = entry.get("description", "")

            if title not in seen:
                seen.add(title)
                articles.append({"title": title, "description": desc})

    return articles[:15]  # 国内は15件


# ============================
#   海外ニュース（NewsAPI）
# ============================
def get_global_news():
    url = (
        "https://newsapi.org/v2/everything?"
        "q=(FOMC) OR (US economy) OR (global markets) "
        "OR (inflation) OR (china economy)&"
        "language=en&"
        "sortBy=publishedAt&"
        "pageSize=10&"
        f"apiKey={NEWS_API_KEY}"
    )
    res = requests.get(url).json()
    articles = res.get("articles", [])

    results = []
    for a in articles:
        results.append({
            "title": a.get("title"),
            "description": a.get("description")
        })

    return results[:5]


# ============================
#        AI 要約
# ============================
def summarize(jp_articles, gl_articles):

    def format_list(lst):
        txt = ""
        for i, a in enumerate(lst, start=1):
            txt += f"① {a['title']}\n"
            txt += f"{a['description']}\n\n\n"
        return txt

    news_text = f"""
【日本のニュース】
{format_list(jp_articles)}

【世界のニュース】
{format_list(gl_articles)}
"""

    prompt = f"""
あなたは金融・経済・政治に精通したトップストラテジストです。
以下のニュースをもとに、金融営業マンが朝に読む
「わかりやすく、かつ分析の精度が高い市場レポート」を作成してください。

【最重要ルール：事実誤認防止】
・ニュース原文に書かれていない“事実の追加・推測”を絶対に行わないこと
  例：政権名・人物名・年代・政策名などを憶測で補完する行為を禁止
・明確に書かれていない事項は「背景として一般的に知られている範囲」で説明する
・具体性を意識するが、必ず「原文と矛盾しない範囲」で記述する
【”5W1Hを意識して” 具体性を高める】
・見出しとして5W1Hを並べる必要はない
・文章は自然な形のままでよい
・ただし内部的に以下の視点を必ず確認し、必要な情報は自然に盛り込み具体性を意識すること：
  - WHEN（いつ）
  - WHERE（どこで）
  - WHO（誰が）
  - WHAT（何を）
  - WHY（なぜ）
  - HOW（どうなった／どう対応した）
・原文に無い項目は「原文では明記されていない」とする


【重要ルール：トピック数について】
・🇯🇵日本のトピックは **必ず12〜18本** の範囲で生成する（厳守）
・🌍世界のトピックは **必ず5〜8本** の範囲で生成する（厳守）
・入力ニュースが少ない場合は、1つのニュースを複数の観点に分解して良い
　例：政策 → 景気 → 為替 → 業界別 など

【全体ルール（超重要）】
・中学生や高校生でも読める“わかりやすさ”は絶対に維持する
・ただし分析フェーズは専門家レベルの精度で「具体的」に書く
・事実（ファクト）は簡潔に、背景と影響は5W1Hを意識して具体的に深掘りする
・説明は抽象表現を避け、ニュースの具体的な内容を引き合いに出す
・必要に応じて政治、法律、外交分野のニュースも積極的に扱う
・数字・固有名詞・比較を使って分析に具体性を持たせる
・因果関係（Aが起きた→その理由→市場にどう影響）を明確に示す

------------------------------------------------
【出力フォーマット】
📊【今日の経済ニュースまとめ】

🇯🇵 日本のトピック（10〜15本：経済中心だが、政治、外交、法律関連も含める）
① 事実（1〜2行：ニュース内容を簡潔に）
   背景（なぜ起きたのか、過去のデータや政策など具体的に）
   影響（株・企業・円・金利・景気にどう影響しうるかを明確に）

（空行2つ）

🌍 世界のトピック（3〜6本）
① 事実（1〜2行）
   背景（地政学・政策・国際関係の要因を具体的に）
   影響（為替・日本企業・世界株にどう波及しうるか）

（空行2つ）

🧭 今日のまとめ（2〜4行）
・今日紹介したトピックの中から重要ニュースを複数引用しつつ、
　市場にとって特に重要な“共通テーマ”を具体的に示す
・抽象的な一般論は禁止。必ず複数ニュースと結びつけて書く

💼 今日の営業ポイント（3つ）
・顧客に説明する際の“具体的な一言サマリー”
・今日の注目点（数字 or イベントを必ず入れる）
・リスクや注意点（これも抽象化せず「○○の件で△△が懸念」など）

------------------------------------------------

【ニュース原文】
{news_text}



【ニュース原文】
{news_text}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは優秀なマーケットアナリストです。"},
            {"role": "user", "content": prompt}
        ]
    )

    return res.choices[0].message.content


# ============================
#       LINE Broadcast
# ============================
def line_broadcast(message):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    res = requests.post(url, headers=headers, json=payload)
    print("LINE response:", res.text)


# ============================
#          main
# ============================
def main():
    jp = get_japan_rss()
    gl = get_global_news()

    report = summarize(jp, gl)

    # 全ユーザーへ一斉配信（無料）
    line_broadcast(report)

    print("送信完了！")


if __name__ == "__main__":
    main()






