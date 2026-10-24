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
st.caption("Hệ thống tra cứu thông minh dựa trên tài liệu độc quyền.")


# Nạp tài liệu tối ưu tốc độ (Không upload trùng lặp)
@st.cache_resource
def load_backend_documents():
  api_key = st.secrets.get("GEMINI_API_KEY")
  if not api_key:
    return None, "Thiếu Gemini API Key trong mục Secrets của Streamlit Cloud!"

  client = genai.Client(api_key=api_key)

  supported_extensions = ["*.pdf", "*.txt", "*.docx"]
  local_files = []
  for ext in supported_extensions:
    local_files.extend(glob.glob(os.path.join(DOCS_FOLDER, ext)))

  if not local_files:
    return None, "Không tìm thấy tài liệu nào trong thư mục documents."

  # Lấy danh sách các file hiện có trên Gemini để kiểm tra
  try:
    existing_files = {f.display_name: f for f in client.files.list()}
  except Exception:
    existing_files = {}

  uploaded_gemini_files = []
  for file_path in local_files:
    file_name = os.path.basename(file_path)

    # Nếu file đã tồn tại trên server Google, tái sử dụng luôn (siêu tốc)
    if file_name in existing_files:
      uploaded_gemini_files.append(existing_files[file_name])
    else:
      # Nếu chưa có thì mới tiến hành upload
      gemini_file = client.files.upload(file=file_path)
      uploaded_gemini_files.append(gemini_file)

  return (client, uploaded_gemini_files), "Thành công"


with st.spinner("Đang khởi động hệ thống tri thức..."):
  result, status_msg = load_backend_documents()

if result is None:
  st.error(f"Lỗi hệ thống: {status_msg}")
  st.stop()

client, backend_files = result

# System Instruction khắt khe
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
              temperature=0.0,
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