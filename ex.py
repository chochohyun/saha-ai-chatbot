import json
import os

# 1. 경로 설정
SOURCE_DIR = './data'           # 원본 데이터가 있는 최상위 폴더
OUTPUT_DIR = './processed_data' # 변환된 파일들이 저장될 폴더

# 저장할 폴더가 없으면 생성
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def transform_logic(item, folder_name):
    """
    각 팀원별로 다른 키 이름을 표준 키로 매핑하는 핵심 로직
    """
    if not isinstance(item, dict):
        return None
        
    return {
        # 제목: title, subject, 제목 중 있는 것을 가져옴
        "title": item.get("title") or item.get("subject") or item.get("제목") or "No Title",
        
        # 내용: content, body, text, 내용 중 있는 것을 가져옴
        "content": item.get("content") or item.get("body") or item.get("text") or item.get("내용") or "",
        
        # 링크: url, link, source 중 있는 것을 가져옴
        "url": item.get("url") or item.get("link") or item.get("source") or "",
        
        # 카테고리: 파일에 정보가 없으면 해당 파일이 속한 폴더명(예: 노인복지)을 사용
        "category": item.get("category") or item.get("type") or item.get("분류") or folder_name
    }

print("🔄 모든 하위 폴더에서 데이터 통합 작업을 시작합니다...")

file_count = 0

# 2. os.walk를 사용하여 하위의 모든 폴더와 파일을 탐색
for root, dirs, files in os.walk(SOURCE_DIR):
    for filename in files:
        if filename.lower().endswith('.json'):
            # 파일의 전체 경로 (예: data/노인복지/all/file.json)
            full_path = os.path.join(root, filename)
            
            # 현재 파일이 속한 직계 폴더 혹은 카테고리 폴더 이름 추출
            # 폴더 구조에 따라 상위 폴더명을 카테고리 기본값으로 활용
            path_parts = root.split(os.sep)
            current_folder = path_parts[1] if len(path_parts) > 1 else "General"

            with open(full_path, 'r', encoding='utf-8') as f:
                try:
                    raw_data = json.load(f)
                    
                    # 파일 내용이 리스트([ ])인지 단일 객체({ })인지 판별하여 변환
                    if isinstance(raw_data, list):
                        refined_data = [transform_logic(obj, current_folder) for obj in raw_data if obj]
                    else:
                        refined_data = transform_logic(raw_data, current_folder)
                    
                    # 3. 저장 단계: 파일명 중복을 피하기 위해 경로를 파일명에 녹여냄
                    # 예: data_노인복지_all_파일명.json
                    new_filename = full_path.replace(os.sep, '_').replace('.', '_') + ".json"
                    save_path = os.path.join(OUTPUT_DIR, new_filename)
                    
                    with open(save_path, 'w', encoding='utf-8') as out_f:
                        json.dump(refined_data, out_f, ensure_ascii=False, indent=4)
                    
                    file_count += 1
                    print(f"[{file_count}] 변환 성공: {full_path}")
                
                except Exception as e:
                    print(f"❌ 에러 발생 ({full_path}): {e}")

print(f"\n✨ 작업 완료! 총 {file_count}개의 파일이 '{OUTPUT_DIR}' 폴더에 정리되었습니다.")