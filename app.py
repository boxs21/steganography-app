import streamlit as st
from PIL import Image
import io
import re
from itertools import cycle
import tempfile
import os

st.set_page_config(page_title="🔐 Steganography Tool", layout="centered")

class Imagen:
    """Clase para esconder y sacar mensajes de fotos usando bitwise."""
    
    def __init__(self, imagen_path_o_bytes):
        """Abre la imagen desde archivo o bytes."""
        if isinstance(imagen_path_o_bytes, bytes):
            self.img = Image.open(io.BytesIO(imagen_path_o_bytes)).convert('RGB')
        else:
            self.img = Image.open(imagen_path_o_bytes).convert('RGB')
    
    def guardar_bytes(self):
        """Devuelve la imagen como bytes para descargar."""
        img_byte_arr = io.BytesIO()
        self.img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    def encode(self, msg, partes):
        """Esconde el mensaje en la foto."""
        # Agregamos delimitadores
        msg_completo = f"&&{msg}&&"
        bytes_msg = [ord(c) for c in msg_completo]
        iterador_msg = cycle(bytes_msg)
        
        # Generador que divide cada letra según el modo
        def generador_bits():
            for letra in iterador_msg:
                if partes == 3:
                    yield (letra >> 5) & 0b111, 0b11111000
                    yield (letra >> 2) & 0b111, 0b11111000
                    yield letra & 0b011, 0b11111100
                    
                elif partes == 6:
                    yield (letra >> 6) & 0b011, 0b11111100
                    yield (letra >> 4) & 0b011, 0b11111100
                    yield (letra >> 3) & 0b001, 0b11111110
                    yield (letra >> 2) & 0b001, 0b11111110
                    yield (letra >> 1) & 0b001, 0b11111110
                    yield letra & 0b001, 0b11111110
                    
                elif partes == 8:
                    yield (letra >> 7) & 0b1, 0b11111110
                    yield (letra >> 6) & 0b1, 0b11111110
                    yield (letra >> 5) & 0b1, 0b11111110
                    yield (letra >> 4) & 0b1, 0b11111110
                    yield (letra >> 3) & 0b1, 0b11111110
                    yield (letra >> 2) & 0b1, 0b11111110
                    yield (letra >> 1) & 0b1, 0b11111110
                    yield letra & 0b1, 0b11111110

        iterador_bits = generador_bits()
        ancho, alto = self.img.size
        
        for y in range(alto):
            for x in range(ancho):
                pixel = list(self.img.getpixel((x, y)))
                
                for i in range(3):
                    parte, mascara = next(iterador_bits)
                    pixel[i] = (pixel[i] & mascara) | parte
                
                self.img.putpixel((x, y), tuple(pixel))

    def _decode_parts(self, partes):
        """Intenta sacar el mensaje con un modo específico."""
        caracteres = []
        ancho, alto = self.img.size
        
        def generador_canales():
            for y in range(alto):
                for x in range(ancho):
                    pixel = self.img.getpixel((x, y))
                    yield pixel[0]
                    yield pixel[1]
                    yield pixel[2]
                        
        canales = generador_canales()
        
        try:
            while True:
                if partes == 3:
                    p1 = next(canales) & 0b111
                    p2 = next(canales) & 0b111
                    p3 = next(canales) & 0b011
                    letra_byte = (p1 << 5) | (p2 << 2) | p3
                    
                elif partes == 6:
                    p1 = next(canales) & 0b011
                    p2 = next(canales) & 0b011
                    p3 = next(canales) & 0b001
                    p4 = next(canales) & 0b001
                    p5 = next(canales) & 0b001
                    p6 = next(canales) & 0b001
                    letra_byte = (p1 << 6) | (p2 << 4) | (p3 << 3) | (p4 << 2) | (p5 << 1) | p6
                    
                elif partes == 8:
                    p1 = next(canales) & 0b1
                    p2 = next(canales) & 0b1
                    p3 = next(canales) & 0b1
                    p4 = next(canales) & 0b1
                    p5 = next(canales) & 0b1
                    p6 = next(canales) & 0b1
                    p7 = next(canales) & 0b1
                    p8 = next(canales) & 0b1
                    letra_byte = (p1 << 7) | (p2 << 6) | (p3 << 5) | (p4 << 4) | (p5 << 3) | (p6 << 2) | (p7 << 1) | p8
                
                caracteres.append(chr(letra_byte))
                
        except StopIteration:
            pass 
            
        texto_completo = "".join(caracteres)
        coincidencias = re.findall(r'&&(.+?)&&', texto_completo)
        
        if coincidencias:
            return min(coincidencias, key=len)
        return None
    
    def decode(self):
        """Saca el mensaje. Intenta automáticamente con 3, 6 y 8."""
        for partes in [8, 6, 3]:  
            resultado = self._decode_parts(partes)
            if resultado is not None:
                return resultado
        
        return None


# ===== INTERFAZ STREAMLIT =====

st.title("🔐 Steganography Tool")
st.markdown("**Esconde mensajes secretos en imágenes usando operadores bitwise**")
st.markdown("---")

# Tabs
tab1, tab2 = st.tabs(["🔒 Codificar", "🔓 Decodificar"])

# ===== TAB 1: CODIFICAR =====
with tab1:
    st.header("Esconde un mensaje en una imagen")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Imagen")
        imagen_subida = st.file_uploader(
            "Sube una imagen (PNG, JPG)", 
            type=['png', 'jpg', 'jpeg'],
            key="encode_image"
        )
    
    with col2:
        st.subheader("Configuración")
        modo = st.selectbox(
            "Modo de codificación",
            [3, 6, 8],
            format_func=lambda x: f"Partes={x}" + (" (Compacto)" if x==3 else " (Balance)" if x==6 else " (Robusto)"),
            key="encode_modo"
        )
        
        modo_info = {
            3: "8 bits/píxel - Máxima capacidad, menos robusto",
            6: "~4 bits/píxel - Balance entre capacidad y robustez",
            8: "~2.7 bits/píxel - Máxima robustez, menos capacidad"
        }
        st.info(modo_info[modo])
    
    st.subheader("Mensaje")
    mensaje = st.text_area(
        "Escribe el mensaje secreto",
        placeholder="Ej: Este es mi mensaje secreto",
        height=100,
        key="encode_mensaje"
    )
    
    if st.button("🔒 Codificar Mensaje", use_container_width=True, key="encode_btn"):
        if imagen_subida is None:
            st.error("❌ Por favor sube una imagen")
        elif not mensaje.strip():
            st.error("❌ Por favor escribe un mensaje")
        else:
            try:
                with st.spinner("Codificando mensaje..."):
                    # Leer imagen
                    imagen_bytes = imagen_subida.read()
                    img = Imagen(imagen_bytes)
                    
                    # Codificar
                    img.encode(mensaje, modo)
                    
                    # Guardar resultado
                    imagen_procesada = img.guardar_bytes()
                    
                    st.success("✅ ¡Mensaje codificado exitosamente!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.image(img.img, caption="Imagen con mensaje oculto")
                    with col2:
                        st.info(f"""
                        📊 **Información:**
                        - Mensaje: `{mensaje}`
                        - Modo: Partes={modo}
                        - Tamaño imagen: {img.img.size}
                        """)
                    
                    st.download_button(
                        label="📥 Descargar imagen (PNG)",
                        data=imagen_procesada,
                        file_name="imagen_secreto.png",
                        mime="image/png",
                        use_container_width=True
                    )
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


# ===== TAB 2: DECODIFICAR =====
with tab2:
    st.header("Recupera un mensaje oculto de una imagen")
    
    imagen_secreta = st.file_uploader(
        "Sube una imagen con mensaje oculto (PNG, JPG)",
        type=['png', 'jpg', 'jpeg'],
        key="decode_image"
    )
    
    if st.button("🔓 Decodificar Mensaje", use_container_width=True, key="decode_btn"):
        if imagen_secreta is None:
            st.error("❌ Por favor sube una imagen")
        else:
            try:
                with st.spinner("Buscando mensaje..."):
                    imagen_bytes = imagen_secreta.read()
                    img = Imagen(imagen_bytes)
                    
                    # Mostrar imagen
                    st.image(img.img, caption="Imagen procesada")
                    
                    # Decodificar
                    mensaje_encontrado = img.decode()
                    
                    if mensaje_encontrado:
                        st.success("✅ ¡Mensaje encontrado!")
                        st.info(f"""
                        📨 **Mensaje oculto:**
                        
                        ```
                        {mensaje_encontrado}
                        ```
                        """)
                        
                        # Copiar al portapapeles
                        st.code(mensaje_encontrado, language="text")
                        
                    else:
                        st.warning("⚠️ No se encontró mensaje en esta imagen")
                        st.info("Posibles razones:\n- La imagen no contiene un mensaje codificado\n- La imagen fue modificada después de codificar")
                        
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# ===== FOOTER =====
st.markdown("---")
st.markdown("""
### 📚 ¿Cómo funciona?

La **esteganografía** es una técnica para esconder información dentro de otras imágenes.

Cada píxel tiene 3 canales (Rojo, Verde, Azul) con valores 0-255. 
Los **bits menos significativos** casi no afectan el color visual, así que modificamos solo esos para guardar el mensaje.

**Modos:**
- **Partes=3**: 3 bits en Rojo, 3 en Verde, 2 en Azul = 1 letra por píxel
- **Partes=6**: Distribuye 6 bits en 2 píxeles = Balance
- **Partes=8**: Distribuye 8 bits en ~3 píxeles = Más robusto

### ⚠️ Importante
- La imagen debe ser lo suficientemente grande para el mensaje
- No comprimas la imagen después de codificar (usa PNG)
- El mensaje se distribuye en toda la imagen (funciona como marca de agua)
""")

st.markdown(f"<div style='text-align: center; color: #888; margin-top: 50px;'>Made with ❤️ | Streamlit</div>", unsafe_allow_html=True)
