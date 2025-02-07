# パーソナリティAIの環境構築について
## 用意するもの
- Google Cloud 
  - プロジェクト（プロジェクトID）
  - サービスアカウント（付与する権限は以下）
    - Cloud Run 起原元　
    - Cloud Speech クライアント
    - Storageオブジェクトユーザー
    - VertexAIユーザー
    - ディスカバリーエンジンユーザー    
  - Cloud Storageにて、以下のバケットとフォルダを用意しておく。
    - バケット : partner-ai
    - フォルダ : diary
  - Agent Builderにて、以下のAgentを作成し、データストアのID（例：search-diary_1234567890xxx_gcs_store）を取得しておく。
    - データストア
      ‐ データソース：cloud storage
      - データの種類：非構造化ドキュメント（PDF、HTML、TXTなど）
      - 周期の頻度：定期的（1日ごと）
      - インポートするフォルダ：partner-ai/diary
      - データコネクタのロケーション：global
      - データコネクタ名：search_diary
    - アプリ
      ‐ アプリの種類：ドキュメント検索
      - アプリ名：search_diary
      - 会社名：partner-ai
      - アプリのロケーション：global
      - データストア：search_diary
  - GitHubから以下のソースコードをダウンロードしておく。
    - https://github.com/INTREPIDA1979/partner-ai-web

## 設定値の更新
- Githubからダウンロードしたプロジェクト（partner-ai-web）の以下のファイルを修正する。
  - src/pages/search_diary.py
  - 修正箇所：14行目,15行目
  - 修正内容1：{project_id} → 対象のプロジェクト名、
  - 修正内容2：{store_id} → Agent Builder作成時に取得したデータスタのID

## Webアプリ環境の構築
以下のコマンドを実行する。
```
#/bin/sh
# set environment valiables
PROJECT_ID={PROJECT_ID}
REGION={REGION}
AR_REPO=partner-ai-web
SERVICE_NAME=partner-ai-web
SA_NAME={SERVICE_ACCONT_NAME}
GOOGLE_API_KEY={GOOGLE_API_KEY}

# プロジェクト設定の変更
gcloud config set project ${PROJECT_ID}

# API有効化
gcloud services enable --project=$PROJECT_ID run.googleapis.com \
 artifactregistry.googleapis.com \
 cloudbuild.googleapis.com \
 compute.googleapis.com \
 aiplatform.googleapis.com \
 iap.googleapis.com \
 discoveryengine.googleapis.com
 generativelanguage.googleapis.com \
 speech.googleapis.com \
 storage.googleapis.com \
 texttospeech.googleapis.com

# Artifacts repositories 作成(Webapp)
gcloud artifacts repositories create $AR_REPO \
 --location=$REGION \
 --repository-format=Docker \
 --project=$PROJECT_ID
  
# PUSH to Artifact Registry
cd
cd $SERVICE_NAME

gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$SERVICE_NAME \
  --project=$PROJECT_ID

# deploy to Cloud Run
gcloud run deploy $SERVICE_NAME --port 8081 \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$SERVICE_NAME \
  --service-account=$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
  --region=$REGION \
  --set-env-vars=PROJECT_ID=$PROJECT_ID,LOCATION=$REGION \
  --project=$PROJECT_ID \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY
```
