import time
import datetime
import streamlit as st

from audio_recorder_streamlit import audio_recorder

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

#from langchain_google_vertexai import VertexAI
from langchain_google_genai import GoogleGenerativeAI
from google.cloud import storage, speech, texttospeech

import logging
import google.cloud.logging

logger = logging.getLogger()
log_client = google.cloud.logging.Client()
log_client.setup_logging()

bucket_name = "partner-ai"

system_prompt = """
あなたは優秀なカウンセラーです。
ユーザからの1日の振り返りを聞いて、アドバイスしてください。
アドバイスはできるだけ100文字以内でお願いします。
"""

save_prompt = """
あなたは優秀なライターです。
次の会話を要約して、箇条書きで1文200文字程度、5～6行程度でまとめてください。
"""

def init_page():
    # タイトルの表示
    st.title('Diary-Chat')
    st.markdown("---")

def init_message_history():
    # message_history がまだ存在しない場合に初期化
    if "message_history" not in st.session_state:
        logger.warning(f"clear")

        st.session_state.message_history = [
            ("system", system_prompt)
        ]
        st.session_state.message_history.append(("assistant", "今日あった出来事を話してください。"))

def init_chain():
    #llm = VertexAI(model="gemini-1.5-flash", location="asia-northeast2")
    llm = GoogleGenerativeAI(model="gemini-1.5-pro")
    prompt = ChatPromptTemplate.from_messages([
        *st.session_state.message_history,
        ("user", "{user_input}") 
    ])
    output_parser = StrOutputParser()
    return prompt | llm | output_parser

def writing_reply(text):
    """
    AIからの返信をストリームっぽく表示する
    """
    message_placeholder = st.empty() # 一時的なプレースホルダーを作成
    assistant_message = ""
    for chunk in text:
        assistant_message += chunk
        message_placeholder.write(assistant_message + "__") # ストリーム表示
        time.sleep(0.02)
    message_placeholder.write(assistant_message) # 最終メッセージ表示

def transcribe_audio_to_text(audio_bytes):
    """
    音声入力をSpeech to Textでテキストに変換
    """
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000,
        language_code="ja-JP",
        audio_channel_count = 2,
    )

    response = client.recognize(config=config, audio=audio)

    reply = ""

    for result in response.results:
        reply += result.alternatives[0].transcript

    return reply

def transcribe_text_to_audio(text):
    """
    テキストをText to Speechで音声に変換
    """
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    return response.audio_content # audio

def save_diary():
    if "message_history" in st.session_state:
        # 会話を要約して、Cloud Storageに保存する。
        llm = GoogleGenerativeAI(model="gemini-1.5-pro")

        prompt = save_prompt
        for role, message in st.session_state.get("message_history", []):
            prompt += "," + role + ":" + message

        response = llm.invoke(prompt)
        logger.warning(f"response: {response}")

        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        today = format(datetime.date.today(), '%Y%m%d')
        blob = bucket.blob(f'diary/diary_' + today + '.txt')
        
        today_str = format(datetime.date.today(), '%Y年%m月%d日')
        with blob.open("w") as f:
            f.write("これは" + today_str + "の日記です。\n" + response)

def main():
    init_page()
    init_message_history()
    chain = init_chain()

    with st.sidebar:
        voice_flg = st.radio('音声出力', ['On', 'Off'])
        # マイク入力
        audio_bytes = audio_recorder(
            text="音声入力はこちら",
            pause_threshold=30
        )    
        save_boolean = st.button("保存", on_click=save_diary)

    # チャット履歴の表示
    for role, message in st.session_state.get("message_history", []):
        if role != "system":
            st.chat_message(role).markdown(message)

    save_btn_flg = False

    if save_boolean:
        save_btn_flg = True

    # チャットボックスの表示＆プロンプト入力時のユーザー・AIチャット表示追加
    if prompt := st.chat_input():
        if save_btn_flg == False:
            st.session_state.message_history.append(("user", prompt))
            st.chat_message("user", avatar=None).write(prompt)
        
            # AIの返答
            reply = get_reply_from_gpt(st.session_state.message_history)
            st.session_state.message_history.append(("assistant", reply))
            with st.chat_message("assistant"):
                writing_reply(reply)
           
    # 音声入力時の処理
    if audio_bytes and save_btn_flg == False:
        # 音声入力のテキスト変換
        transcript = transcribe_audio_to_text(audio_bytes)
        st.chat_message("user").write(transcript)

        # AIの返答
        with st.chat_message('assistant'):
            response = st.write_stream(chain.stream({"user_input": transcript}))
#            logger.warning(f"response: {response}")
        
        if voice_flg == "On":
            # [TODO] responseがマークダウン形式になっており、***とかを読み上げちゃうので、対策が必要。
            # とりあえず、***を除去しておくことで最低限の対策はしておくが、LLMで除去した方が良さそう。
            response_remove_mark = response.replace('*', '')
            response_audio = transcribe_text_to_audio(response_remove_mark)
            st.audio(response_audio, format="audio/mp3", autoplay=True)

        # チャット履歴に追加
        st.session_state.message_history.append(("user", transcript))
        st.session_state.message_history.append(("assistant", response))

    if save_btn_flg == True:
        st.chat_message("system").write("日記を保存しました")

if __name__ == '__main__':
    main()