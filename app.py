import glob
import os
from google import genai
from google.genai import types
import streamlit as st

DOCS_FOLDER = "./documents"

# Cấu hình giao diện web tối giản
st.set_page_config(
    page_title="Trợ Lý Hỏi Đáp Kiến Thức", page_icon="📖", layout="centered"
)
st.title("📖 Trợ Lý Hỏi - Đáp Kiến Thức Giáo Dục")
st.caption("Hệ thống trả lời dựa trên tài liệu độc quyền của trường/lớp.")


# Nạp tài liệu nguồn ngầm từ Backend
@st.cache_resource
def load_backend_documents():
  api_key = st.secrets.get("GEMINI_API_KEY")
  if not api_key:
    return None, "Thiếu Gemini API Key trong mục Secrets của Streamlit Cloud!"

  client = genai.Client(api_key=api_key)

  supported_extensions = ["*.pdf", "*.txt", "*.docx"]
  files_to_upload = []
  for ext in supported_extensions:
    files_to_upload.extend(glob.glob(os.path.join(DOCS_FOLDER, ext)))

  if not files_to_upload:
    return None, "Không tìm thấy tài liệu nào trong thư mục documents."

  uploaded_gemini_files = []
  for file_path in files_to_upload:
    with open(file_path, "rb") as f:
      gemini_file = client.files.upload(file=f)
      uploaded_gemini_files.append(gemini_file)

  return (client, uploaded_gemini_files), "Thành công"


result, status_msg = load_backend_documents()
if result is None:
  st.error(f"Lỗi hệ thống: {status_msg}")
  st.stop()

client, backend_files = result

# System Instruction khắt khe: Không tìm nguồn ngoài, bắt buộc báo không tìm thấy
STRICT_SYSTEM_INSTRUCTION = """
Bạn là một hệ thống tra cứu tài liệu nội bộ chính xác tuyệt đối. 
Nhiệm vụ của bạn là đọc các tài liệu được cung cấp ngầm và trả lời câu hỏi của người dùng.

BẮT BUỘC TUÂN THỦ CÁC QUY TẮC SAU:
1. CHỈ ĐƯỢC PHÉP sử dụng thông tin có sẵn bên trong các tài liệu nguồn được đính kèm. 
2. TUYỆT ĐỐI KHÔNG sử dụng kiến thức bên ngoài, không tự suy diễn, không tự suy luận ngoài văn bản.
3. Nếu thông tin không có trong tài liệu nguồn, bạn PHẢI trả lời chính xác câu sau: 
   "Xin lỗi, tôi không tìm thấy thông tin này trong tài liệu được cung cấp."
4. Không được phép tự ý bịa ra câu trả lời dưới bất kỳ hình thức nào.
"""

# Giao diện khung chat / hỏi đáp
if "history" not in st.session_state:
  st.session_state.history = []

user_query = st.chat_input("Nhập câu hỏi của bạn tại đây...")

if user_query:
  st.session_state.history.append({"role": "user", "content": user_query})
  contents = list(backend_files) + [user_query]

  with st.spinner("Đang tra cứu tài liệu..."):
    try:
      response = client.models.generate_content(
          model="gemini-2.5-flash",
          contents=contents,
          config=types.GenerateContentConfig(
              system_instruction=STRICT_SYSTEM_INSTRUCTION,
              temperature=0.0,  # 0.0 để ép AI tuyệt đối bám sát văn bản, không sáng tác
          ),
      )
      answer = response.text
      st.session_state.history.append({"role": "assistant", "content": answer})
    except Exception as e:
      st.session_state.history.append(
          {"role": "assistant", "content": f"Đã xảy ra lỗi hệ thống: {e}"}
      )

# Hiển thị lịch sử hỏi đáp
for item in st.session_state.history:
  if item["role"] == "user":
    with st.chat_message("user"):
      st.write(item["content"])
  else:
    with st.chat_message("assistant"):
      st.write(item["content"])