import time
import streamlit as st

# audio 
from audio_recorder_streamlit import audio_recorder
from google.cloud import storage, speech, texttospeech

# agent
from vertexai import generative_models
import vertexai.preview.generative_models as generative_models
from vertexai.generative_models import GenerativeModel, Tool

# initial set
project_id = "{project_id}"
store_id = "{store_id}"
datastore_id = "projects/" + project_id + "/locations/global/collections/default_collection/dataStores/" + store_id

system_prompt = f"""あなたは優秀なAIエージェントです。ユーザーからの質問に分かりやすく回答してください。"""

def ai_agent(user_message):
    tools = [
        Tool.from_retrieval(
            retrieval=generative_models.grounding.Retrieval(
                source=generative_models.grounding.VertexAISearch(datastore=datastore_id),
                disable_attribution=False,
            )
        ),
    ]

    model = GenerativeModel(
        "gemini-1.5-flash-002",
        system_instruction=[
            system_prompt,
        ],
        tools=tools,
    )

    response = model.generate_content(
    user_message,
    generation_config={
        "max_output_tokens": 4000,
        "temperature": 0,
        "top_p": 1,
        "top_k": 32
    },
    stream=False
    )

    try:
        print(response.candidates[0].content.parts[0].text)
        answer = response.candidates[0].content.parts[0].text
    except:
        print(response)
        answer = "もう一度わかりやすく質問してください！"
    return answer

def writing_reply(text):
    """
    AIからの返信をストリームっぽく表示する
    """
    message_placeholder = st.empty() # 一時的なプレースホルダーを作成
    assistant_message = ""
    for chunk in text:
        assistant_message += chunk
        message_placeholder.write(assistant_message + "__") # カーソルのようなものとともにストリーム表示
        time.sleep(0.02)
    message_placeholder.write(assistant_message) # 最終的なメッセージを表示

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
#        logger.warning(f"Transcript: {result.alternatives[0].transcript}")

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

def main():
    # タイトルの表示
    st.title('Search Diary')
    st.markdown("---")

    with st.sidebar:
        voice_flg = st.radio('音声出力', ['On', 'Off'])
        # マイク入力
        audio_bytes = audio_recorder(
            text="音声入力はこちら",
            pause_threshold=30
        )    

    # チャットボックスの表示＆プロンプト入力時のユーザー・AIチャット表示追加
    if prompt := st.chat_input():
        st.chat_message("user", avatar=None).write(prompt)
        
        # AIの返答
        reply = ai_agent(prompt)
        with st.chat_message("assistant"):
            writing_reply(reply)
           
    # 音声入力時の処理
    if audio_bytes:
        # 音声入力のテキスト変換
        transcript = transcribe_audio_to_text(audio_bytes)
        st.chat_message("user").write(transcript)

        # AIの返答
        response = ai_agent(transcript)
        with st.chat_message("assistant"):
            writing_reply(response)
        
        if voice_flg == "On":
            # [TODO] responseがマークダウン形式になっており、***とかを読み上げちゃうので、対策が必要。
            # とりあえず、***を除去しておくことで最低限の対策はしておくが、LLMで除去した方が良さそう。
            response_remove_mark = response.replace('*', '')
            response_audio = transcribe_text_to_audio(response_remove_mark)
            st.audio(response_audio, format="audio/mp3", autoplay=True)

if __name__ == '__main__':
    main()
