import deepl
import json
import jieba
import opencc
from pypinyin import pinyin, Style
from openai import OpenAI
import string
import translators as ts
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI() 
my_secret_key = os.getenv("DEEP_L_API_KEY")
translator = deepl.Translator(my_secret_key)


chinese_punctuation = '，。！？：；“”‘’（）《》【】、'
all_punctuation = string.punctuation + chinese_punctuation
converter = opencc.OpenCC('s2t')
manual_chars = {
    '是': 'is',
    '的': 'of',
    '在': 'at',
    '有': 'have',
    '和': 'and',
    '不': 'not',
    '这': 'this',
    '那': 'that',
    '做': 'make/do',
    '来': 'come',
    '曰': 'said',
    '地': '(used to connect and adj/adv with a verb)',
    '用': 'use/need'
}

def translate(chinese_text):
    response = client.chat.completions.create(
        model='gpt-4o-mini',  
        messages=[
            {"role": "system", "content": "Translate the following Chinese sentence into English. Send back the sentence in English and nothing else."},
            {"role": "user", "content": chinese_text}
        ],
    )
    return response.choices[0].message.content


def process_chapters(data):
    for chapter in data["chapters"]:
        chapter['chapter_title_traditional'] = converter.convert(chapter['chapter_title_simplified'])
        for hsk_level in chapter["hsk_levels"]:
            if 'segments' in hsk_level:
                print(f"Chapter {chapter['chapter_number']} level {hsk_level['level']} already done")
                continue  # Skip this hsk_level if 'segments' already exists

            # Initialize missing fields
            hsk_level['segments'] = []
            if 'translated_sentences' not in hsk_level:
                hsk_level['translated_sentences'] = []

            # Segment the simplified text
            simplified_segmented = list(jieba.cut(hsk_level['simplified_text']))
            original_sentences = hsk_level['simplified_text'].split('。')

            sentence_number = 0
            for segment in simplified_segmented:
                segment_info = {
                    'simplified': segment,
                    'traditional': converter.convert(segment),
                    'pinyin': " ".join([item[0] for item in pinyin(segment, style=Style.TONE)]),
                    'sentence': sentence_number
                }

                # Check if simplified, traditional, and pinyin are the same
                if segment_info['simplified'] == segment_info['traditional'] and segment_info['simplified'] == segment_info['pinyin']:
                    segment_info['english'] = segment
                    if '.' in segment or '。' in segment:
                        hsk_level['translated_sentences'].append(translate(original_sentences[sentence_number]))
                        sentence_number += 1
                else:
                    # Translate the segment
                    if segment in manual_chars:
                        segment_info['english'] = manual_chars[segment]
                    else:
                        try:
                            # segment_info['english'] = ts.translate_text(query_text=segment, from_language='zh', to_language='en')
                            # segment_info['english'] = ts.translate_text(query_text=segment, translator='yandex', from_language='zh', to_language='en')
                            asEnglish = translator.translate_text(segment, source_lang="ZH", target_lang="EN-US")
                            segment_info['english'] = asEnglish.text

                        except:
                            print(f"Translation failed for segment: {segment}")
                            segment_info['english'] = "Translation unavailable"
                
                hsk_level['segments'].append(segment_info)

        print(f"Chapter {chapter['chapter_number']} done now")
        save_to_file(data)
    return data

text_name = "storyOfAnHour.json"

def save_to_file(data, file_name=text_name):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    with open(text_name, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated_data = process_chapters(data)

    save_to_file(updated_data)
    print("Segmentation, Pinyin, and Translation completed and saved to segmented.json")
