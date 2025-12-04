# Wslll Blog

[English](#english) | [中文](#chinese)

<a name="english"></a>

## English

Wslll Blog is a feature-rich, bilingual (Chinese/English) blog system built with Flask. It integrates AI capabilities via DeepSeek for content translation and summarization, features a photo gallery, and supports SMS login.

### Features

*   **Bilingual Support**: Seamlessly switch between Chinese and English content.
*   **AI Integration**: Uses DeepSeek API for automatic translation of posts and generating summaries.
*   **Content Management**: Create, edit, and delete blog posts with Markdown support.
*   **Photo Gallery**: Upload and manage photos with descriptions.
*   **Authentication**:
    *   Traditional username/password login.
    *   SMS Login via Spug Push.
*   **Global Notifications**: Site-wide notifications configurable via settings.
*   **Responsive Design**: Clean and modern interface.

### Tech Stack

*   **Backend**: Python, Flask
*   **Database**: SQLite (via SQLAlchemy)
*   **Frontend**: HTML, CSS, Bootstrap
*   **AI**: DeepSeek API
*   **Other**: Flask-Login, Flask-WTF, Markdown

### Installation

1.  **Clone the repository**
    ```bash
    git clone <repository_url>
    cd wslll_blog
    ```

2.  **Install dependencies**
    It is recommended to use a virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    # Ensure additional dependencies are installed
    pip install requests openai
    ```

### Configuration

1.  **Database**: The application uses SQLite. The database `blog.db` will be automatically created on the first run if it doesn't exist.

2.  **DeepSeek API**:
    To enable AI features, you need to configure your DeepSeek API key. You can do this through the admin settings panel after logging in.

3.  **Secret Key**:
    For production use, ensure you update the `SECRET_KEY` in `app.py`.

### Usage

1.  **Run the application**
    ```bash
    python app.py
    ```
    The server will start on `http://0.0.0.0:15013`.

2.  **Access the blog**
    Open your browser and visit `http://localhost:15013`.

3.  **Admin Login**
    *   **Default Username**: `admin`
    *   **Default Password**: `admin123`
    
    *Please change the password immediately after your first login via the Settings page.*

### Project Structure

```
wslll_blog/
├── app.py              # Main application entry point and logic
├── models.py           # Database models
├── requirements.txt    # Python dependencies
├── static/             # Static files (CSS, JS, Uploads)
└── templates/          # HTML Templates
```

---

<a name="chinese"></a>

## 中文

Wslll Blog 是一个基于 Flask 构建的功能丰富的双语（中/英）博客系统。它通过 DeepSeek 集成了 AI 能力，用于内容翻译和摘要生成，同时具备照片墙功能，并支持短信验证码登录。

### 功能特性

*   **双语支持**：无缝切换中文和英文内容。
*   **AI 集成**：使用 DeepSeek API 自动翻译文章并生成摘要。
*   **内容管理**：支持 Markdown 的博客文章创建、编辑和删除。
*   **照片墙**：上传和管理带有描述的照片。
*   **身份验证**：
    *   传统的用户名/密码登录。
    *   通过 Spug Push 的短信验证码登录。
*   **全局通知**：可通过设置配置的全站通知。
*   **响应式设计**：简洁现代的界面。

### 技术栈

*   **后端**：Python, Flask
*   **数据库**：SQLite (通过 SQLAlchemy)
*   **前端**：HTML, CSS, Bootstrap
*   **AI**：DeepSeek API
*   **其他**：Flask-Login, Flask-WTF, Markdown

### 安装指南

1.  **克隆仓库**
    ```bash
    git clone <repository_url>
    cd wslll_blog
    ```

2.  **安装依赖**
    建议使用虚拟环境。
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Windows 系统使用: venv\Scripts\activate
    pip install -r requirements.txt
    # 确保安装了额外的依赖
    pip install requests openai
    ```

### 配置说明

1.  **数据库**：应用使用 SQLite。如果 `blog.db` 不存在，首次运行时会自动创建。

2.  **DeepSeek API**：
    要启用 AI 功能，您需要配置 DeepSeek API 密钥。登录后，您可以在管理员设置面板中进行配置。

3.  **密钥配置 (Secret Key)**：
    在生产环境中，请务必更新 `app.py` 中的 `SECRET_KEY`。

### 使用说明

1.  **运行应用**
    ```bash
    python app.py
    ```
    服务器将在 `http://0.0.0.0:15013` 启动。

2.  **访问博客**
    打开浏览器并访问 `http://localhost:15013`。

3.  **管理员登录**
    *   **默认用户名**：`admin`
    *   **默认密码**：`admin123`
    
    *请在首次登录后立即在设置页面修改密码。*

### 项目结构

```
wslll_blog/
├── app.py              # 主应用程序入口和逻辑
├── models.py           # 数据库模型
├── requirements.txt    # Python 依赖项
├── static/             # 静态文件 (CSS, JS, Uploads)
└── templates/          # HTML 模板
```
