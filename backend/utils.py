
import streamlit as st

#########Roda pé##########
def render_footer():
    footer_html = """
    <style>
    footer { visibility: hidden; }
    .main .block-container { padding-bottom: 60px; }
    .custom-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #f2f2f2; text-align: center;
        padding: 10px 0; font-size: 14px; color: #666;
    }
    .icon { width: 20px; height: 20px; vertical-align: middle; margin-right: 5px; border-radius: 4px; }
    </style>
    <div class="custom-footer">
        Feito por <strong>Marcelo Cabreira Bastos</strong> | 
        Contato: <a href="mailto:marcelo.cabreira@mda.gov.br">marcelo.cabreira@mda.gov.br</a> | 
        <a href="https://www.linkedin.com/in/marcelo-cabreira-bastos/" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/512/174/174857.png" alt="LinkedIn" class="icon">
            LinkedIn
        </a> |
        <a href="https://api.whatsapp.com/send?phone=5561981983931" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/512/124/124034.png" alt="WhatsApp" class="icon">
            WhatsApp
        </a>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

#########Roda pé##########
