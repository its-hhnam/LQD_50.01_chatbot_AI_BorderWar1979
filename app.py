import glob
import os
import time
from google import genai
from google.genai import types
import streamlit as st

DOCS_FOLDER = "./document"

# Cấu hình giao diện web tối giản
st.set_page_config(
    page_title="Chatbot AI - Chiến tranh Biên giới Tây Nam 1979",
    page_icon="📖",
    layout="centered",
)
st.title("📖 Chatbot AI - Chiến tranh Biên giới Tây Nam 1979")
st.caption("Tạo bởi 12A5 THPT Lê Quý Đôn - Dự án Liên môn 50.01 | Hoạt động dựa vào AI model Gemini 3.8 Flash")
st.caption("Lưu ý: Chatbot được xây dựng trên model miễn phí, khuyến khích né giờ cao điểm 20h-02h và nên truy cập vào buổi sáng")


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
    return None, "Không tìm thấy tài liệu nào trong thư mục document."

  # Lấy danh sách các file ACTIVE hiện có trên Gemini để tái sử dụng
  try:
    existing_files = {
        f.display_name: f
        for f in client.files.list()
        if getattr(f, "display_name", None)
        and getattr(getattr(f, "state", None), "name", None) == "ACTIVE"
    }
  except Exception:
    existing_files = {}

  uploaded_gemini_files = []
  for file_path in local_files:
    file_name = os.path.basename(file_path)

    # Nếu file đã tồn tại trên server Google ở trạng thái ACTIVE, tái sử dụng luôn
    if file_name in existing_files:
      uploaded_gemini_files.append(existing_files[file_name])
    else:
      # Upload kèm display_name để Files API lưu tên file gốc
      gemini_file = client.files.upload(
          file=file_path,
          config=types.UploadFileConfig(display_name=file_name),
      )
      # Chờ nếu file đang trong quá trình xử lý (đối với tài liệu lớn/PDF)
      while getattr(getattr(gemini_file, "state", None), "name", None) == "PROCESSING":
        time.sleep(1)
        gemini_file = client.files.get(name=gemini_file.name)

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

# Khởi tạo lịch sử chat
if "history" not in st.session_state:
  st.session_state.history = []

# 1. Hiển thị lịch sử hỏi đáp hiện có
for item in st.session_state.history:
  with st.chat_message(item["role"]):
    st.write(item["content"])

# 2. Xử lý câu hỏi mới từ người dùng
user_query = st.chat_input("Nhập câu hỏi của bạn tại đây...")

if user_query:
  # Hiển thị ngay câu hỏi của user trên giao diện
  with st.chat_message("user"):
    st.write(user_query)
  st.session_state.history.append({"role": "user", "content": user_query})

  contents = list(backend_files) + [user_query]

  # Hiển thị câu trả lời của trợ lý
  with st.chat_message("assistant"):
    with st.spinner("Đang tra cứu tài liệu..."):
      try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=STRICT_SYSTEM_INSTRUCTION,
                temperature=0.0,
            ),
        )
        answer = response.text
        st.write(answer)
        st.session_state.history.append({"role": "assistant", "content": answer})
      except Exception as e:
        error_msg = f"Đã xảy ra lỗi hệ thống: {e}"
        st.error(error_msg)
        st.session_state.history.append(
            {"role": "assistant", "content": error_msg}
        )
