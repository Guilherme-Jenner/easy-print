import sys
import os
import glob
import time
import subprocess
import argparse
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, 
    QPushButton, QHBoxLayout, QVBoxLayout, QSystemTrayIcon, QMenu, QFileDialog
)
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap
import math

class EasyPrint(QWidget):
    def __init__(self):
        super().__init__()

        # ==========================================
        # MÓDULO IPC (Servidor Local para receber comandos)
        # ==========================================
        self.servidor = QLocalServer(self)
        self.servidor.removeServer("easyprint_socket") # Limpa sujeira de execuções passadas
        self.servidor.listen("easyprint_socket")
        self.servidor.newConnection.connect(self.receber_comando_externo)
        
        self.pixmap_atual = None
        self.rect_imagem = QRect()
        self.linhas_desenhadas = []
        self.ponto_inicio_desenho = None
        self.ponto_fim_desenho = None
        self.esta_desenhando = False
        self.seta_ativada = False
        self.retangulo_ativado = False

        self.setWindowFlags(Qt.FramelessWindowHint| Qt.WindowStaysOnTopHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Evita que o app feche completamente se todas as janelas sumirem
        QApplication.setQuitOnLastWindowClosed(False)
        self.tray_icon = QSystemTrayIcon(self)
        # (Opcional) Tente colocar um caminho de ícone válido .png aqui depois
        # self.tray_icon.setIcon(QIcon("icone.png")) 
        
        # Cria o menu do botão direito no ícone do relógio
        tray_menu = QMenu()
        acao_print = tray_menu.addAction("Tirar Print")
        acao_print.triggered.connect(self.tirar_print)

        acao_ocultar = tray_menu.addAction("Ocultar")
        acao_ocultar.triggered.connect(self.ocultar_menu)

        acao_sair = tray_menu.addAction("Encerrar Easy-Print")
        acao_sair.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    def ocultar_menu(self):
        if self.tray_icon is not None:
            self.tray_icon.hide()

    def receber_comando_externo(self):
        socket = self.servidor.nextPendingConnection()
        socket.waitForReadyRead(100)
        mensagem = socket.readAll().data().decode('utf-8')
        
        if mensagem == "PRINT":
            print("🚀 Comando externo recebido! Disparando print...")
            self.tirar_print()
        
        socket.disconnectFromServer()

    def iniciar_edicao(self, pixmap):
        # 1. Armazena a imagem que pegamos do disco ou clipboard
        self.pixmap_atual = pixmap

        self.showNormal()      # Tira a janela do estado "escondido" (hide)
        self.showMaximized()  # Força a tela cheia
        self.raise_()          # Traz a janela para a frente de tudo (Z-Index)
        self.activateWindow()  # Exige o foco do teclado/mouse para o app

        
        # 1. Força o Linux a atualizar as dimensões da tela após o FullScreen
        QApplication.processEvents() 

        # 2. CALCULA A POSIÇÃO DA IMAGEM ANTES DO MENU!
        self.rect_imagem = self.pixmap_atual.rect()
        self.rect_imagem.moveCenter(self.rect().center())
        
        # 2. Criamos o painel passando 'self' como pai
        self.painel = QFrame(self) 
        self.painel.setStyleSheet("""
            background-color: #333; 
            border-radius: 8px;
            border: 1px solid #555;
        """)

        botao_fixed_height = 30
        qntd_botoes = 4
        valor_margin = 10
        button_style_pattern = "background-color: #48BBC5; color: white; border: none; border-radius: 4px;"

        self.painel.setFixedSize(70, (botao_fixed_height * qntd_botoes) + (valor_margin * (qntd_botoes))) 
        
        # 3. Criamos um layout para os botões dentro do painel
        layout = QVBoxLayout(self.painel)
         
        btn_seta = QPushButton("Arrow", self.painel)
        btn_retangulo = QPushButton("Box", self.painel) 
        btn_copiar = QPushButton("Copy", self.painel)
        btn_salvar = QPushButton("Save", self.painel)

        btn_seta.setStyleSheet(button_style_pattern)
        btn_retangulo.setStyleSheet(button_style_pattern)
        btn_copiar.setStyleSheet(button_style_pattern)
        btn_salvar.setStyleSheet(button_style_pattern)

        btn_seta.setFixedHeight(botao_fixed_height)
        btn_retangulo.setFixedHeight(botao_fixed_height)
        btn_copiar.setFixedHeight(botao_fixed_height)
        btn_salvar.setFixedHeight(botao_fixed_height)

        btn_seta.clicked.connect(self.ativar_modo_seta)
        btn_retangulo.clicked.connect(self.ativar_modo_retangulo)
        btn_copiar.clicked.connect(self.acao_copiar)
        btn_salvar.clicked.connect(self.acao_salvar)

        layout.addWidget(btn_seta)
        layout.addWidget(btn_retangulo)
        layout.addWidget(btn_copiar)
        layout.addWidget(btn_salvar)
        layout.setAlignment(Qt.AlignTop)

        # 4. Mostra o painel (ele aparecerá no canto superior esquerdo por padrão)
        if self.painel.x() == 0 and self.painel.y() == 0:
            self.posicionar_menu() # Se o painel ainda estiver no canto, reposiciona ele do lado da imagem

        self.painel.show()
        self.update() # Força o paintEvent a desenhar o fundo e a imagem

    def tirar_print(self):

        comando = [
            "cosmic-screenshot",
            "--interactive=true"
        ]
        inicio_do_processo = time.time()

        subprocess.run(comando)
        time.sleep(0.5)

        foto_salva = self.localizar_print_interativo(inicio_do_processo)

        if foto_salva:
            print(f"🔥 Achou no disco: {foto_salva}")
            # Transforma o caminho do arquivo em um QPixmap e inicia!
            self.iniciar_edicao(QPixmap(foto_salva))

            try:
                os.remove(foto_salva)
                print(f"🧹 Lixo limpo: Arquivo temporário apagado.")
            except Exception as e:
                print(f"⚠️ Aviso: Não foi possível apagar o arquivo original: {e}")
        else:
            foto_clipboard = self.buscar_da_area_transferencia()
            if foto_clipboard:
                print("🔥 Achou no clipboard!")
                print(foto_clipboard)
                self.iniciar_edicao(foto_clipboard)
            else:
                print("❌ Nenhum print detectado. Fechando...")
                self.hide() # A janela some da tela, mas o código continua vivo na memória

    def localizar_print_interativo(self, tempo_print):
    # Lista de lugares onde o sistema costuma salvar
        buscas = [
            "~/Imagens/Screenshots/*.png",
            "~/Imagens/*.png",
            "~/Documentos/*.png"
        ]
    
        arquivos_encontrados = []
    
        for padrao in buscas:
            # Resolve o '~' para o caminho real (ex: /home/jenner/...)
            caminho_completo = os.path.expanduser(padrao)
            # Pega todos os arquivos que batem com o padrão .png
            arquivos_encontrados.extend(glob.glob(caminho_completo))
    
        if not arquivos_encontrados:
            return None

        # Pegamos o arquivo com a data de modificação (mtime) mais recente
        ultimo_arquivo = max(arquivos_encontrados, key=os.path.getmtime)
    
        # Validação de segurança: o arquivo deve ter sido criado há poucos segundos
        # (Evita que o Python abra um print velho que já estava na pasta)
        if tempo_print - os.path.getmtime(ultimo_arquivo) < 3: # 3 segundos
            return ultimo_arquivo
    
        return None
    
    def buscar_da_area_transferencia(self):
        clipboard = QApplication.clipboard()
        
        # 1. TENTATIVA OFICIAL (Qt)
        # Tenta 5 vezes pelo caminho normal (pode funcionar se o app não perdeu o foco 100%)
        for i in range(3):
            QApplication.processEvents() 
            mime_data = clipboard.mimeData()
            if mime_data.hasImage():
                return clipboard.pixmap()
            time.sleep(0.5)
            
        # 2. FALLBACK TÁTICO (Wayland Raw Memory)
        # Se o Qt falhou por falta de permissão de foco, vamos direto ao servidor gráfico!
        print("⚠️ Qt bloqueado pelo Wayland. Tentando via wl-paste...")
        try:
            # Executa o wl-paste pedindo especificamente o formato de imagem
            resultado = subprocess.run(["wl-paste", "-t", "image/png"], capture_output=True)
            
            # Se o comando deu certo e retornou bytes (a imagem em si)
            if resultado.returncode == 0 and len(resultado.stdout) > 0:
                print("✅ Imagem resgatada da memória via wl-paste!")
                
                # Converte os bytes puros em um QPixmap do PySide6
                from PySide6.QtGui import QPixmap
                pixmap_salvo = QPixmap()
                pixmap_salvo.loadFromData(resultado.stdout)
                
                return pixmap_salvo
        except FileNotFoundError:
            print("❌ Comando wl-paste não encontrado no sistema.")
        except Exception as e:
            print(f"❌ Erro ao ler memória: {e}")
            
        return None
    
    def paintEvent(self, event):
        if not self.pixmap_atual:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))

        if self.pixmap_atual:
            self.rect_imagem = self.pixmap_atual.rect()
            self.rect_imagem.moveCenter(self.rect().center())

        # 3. Desenhar a imagem
        painter.drawPixmap(self.rect_imagem, self.pixmap_atual)

        # 4. Desenhar borda na imagem para destacar
        pen = QPen(QColor(72, 187, 197), 2)
        painter.setPen(pen)
        painter.drawRect(self.rect_imagem)

        # ==========================================
        # 5. MÓDULO DE DESENHO (O que entra de novo!)
        # ==========================================
        
        # Muda a caneta para desenhar os traços vermelhos
        pen_desenho = QPen(QColor(255, 50, 50), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen_desenho)

        for linha in self.linhas_desenhadas:
            ferramenta, ponto_a, ponto_b = linha
            if ferramenta == 'linha':
                painter.drawLine(ponto_a, ponto_b)
            elif ferramenta == 'retangulo':
                # O QRect magicamente normaliza o Ponto A e o Ponto B num quadrado
                painter.drawRect(QRect(ponto_a, ponto_b))
            else:
                self.desenhar_seta_com_math(painter, ponto_a, ponto_b)

        # Desenha a linha atual ("fantasma") enquanto arrasta o mouse
        if getattr(self, 'esta_desenhando', False) and self.ponto_inicio_desenho and self.ponto_fim_desenho:
            if getattr(self, 'seta_ativada', False):
                self.desenhar_seta_com_math(painter, self.ponto_inicio_desenho, self.ponto_fim_desenho)
            elif getattr(self, 'retangulo_ativado', False):
                painter.drawRect(QRect(self.ponto_inicio_desenho, self.ponto_fim_desenho))
            else:
                # Se não, desenha apenas um traço reto normal (Lápis)
                painter.drawLine(self.ponto_inicio_desenho, self.ponto_fim_desenho)

    def resizeEvent(self, event):
        # Garante que o comportamento padrão do Qt continue funcionando
        super().resizeEvent(event)
        
        # Só tenta reposicionar se o app já estiver com a foto carregada e o menu criado
        if self.pixmap_atual and hasattr(self, 'painel'):
            # 1. Recalcula onde a imagem deve ficar agora que a tela mudou de tamanho
            self.rect_imagem = self.pixmap_atual.rect()
            self.rect_imagem.moveCenter(self.rect().center())
            
            # 2. Manda o menu acompanhar a nova posição da imagem
            self.posicionar_menu()

    def desenhar_seta_com_math(self, painter, p1, p2):
        # 1. Desenha a linha principal ("corpo" da seta)
        painter.drawLine(p1, p2)
        
        # Parâmetros de design da seta
        tamanho_ponta = 25
        angulo_abertura = math.pi / 6  # Equivalente a 30 graus em radianos

        # 2. Calcula a diferença entre X e Y
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        
        # 3. Descobre o ângulo da linha principal
        angulo_linha = math.atan2(dy, dx)

        # 4. Calcula o Ponto da Aba Esquerda
        # (Ângulo da linha + 180 graus - 30 graus)
        angulo_esq = angulo_linha + math.pi - angulo_abertura
        x_esq = p2.x() + tamanho_ponta * math.cos(angulo_esq)
        y_esq = p2.y() + tamanho_ponta * math.sin(angulo_esq)
        ponto_esq = QPoint(int(x_esq), int(y_esq)) # QPoint exige números inteiros

        # 5. Calcula o Ponto da Aba Direita
        # (Ângulo da linha + 180 graus + 30 graus)
        angulo_dir = angulo_linha + math.pi + angulo_abertura
        x_dir = p2.x() + tamanho_ponta * math.cos(angulo_dir)
        y_dir = p2.y() + tamanho_ponta * math.sin(angulo_dir)
        ponto_dir = QPoint(int(x_dir), int(y_dir))

        # 6. Desenha as duas pontas a partir do Ponto B
        painter.drawLine(p2, ponto_esq)
        painter.drawLine(p2, ponto_dir)

    def posicionar_menu(self):
        # 1. Tenta colocar 15 pixels para fora da imagem
        x = self.rect_imagem.right() + 2
        y = self.rect_imagem.center().y() - (self.painel.height() // 2)
        
        # 2. Nova Trava de Segurança
        # em vez de jogar de volta para dentro da imagem.
        print(self.width(), self.rect_imagem.right(), self.painel.width())
        limite_da_tela = self.width() - self.painel.width() - 2
        if x > limite_da_tela:
            x = limite_da_tela

        self.painel.move(x, y)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.limparPrintAntigo()
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
            self.removerUltimaEdicao()

    def limparPrintAntigo(self):
        self.linhas_desenhadas.clear() 
        self.painel.hide() # Fecha o painel de ferramentas

        #self.update()
        self.hide() # A janela some da tela, mas o código continua vivo na memória
    
    def removerUltimaEdicao(self):
        if len(self.linhas_desenhadas) > 0:
            # Remove a última ação (linha ou seta) guardada na memória
            self.linhas_desenhadas.pop() 
            
            # ATENÇÃO: O update() é vital aqui! Ele diz ao paintEvent 
            # para "limpar a tela e desenhar tudo de novo", mas agora 
            # sem a linha que acabamos de apagar.
            self.update() 
            print("↩️ Desfazer: Última edição removida!")
        else:
            print("⚠️ Nada para desfazer.")

    def mousePressEvent(self, event):
        # Se o usuário clicar com o botão esquerdo, começamos a desenhar
        if event.button() == Qt.LeftButton:
            self.esta_desenhando = True
            self.ponto_inicio_desenho = event.position().toPoint()
            self.ponto_fim_desenho = self.ponto_inicio_desenho

    def mouseMoveEvent(self, event):
        # Atualiza a linha "fantasma" enquanto o mouse é arrastado
        if self.esta_desenhando:
            self.ponto_fim_desenho = event.position().toPoint()
            self.update() # Chama o paintEvent para redesenhar a tela rapidamente

    def mouseReleaseEvent(self, event):
        # Quando soltar o botão, salva a linha na memória
        if event.button() == Qt.LeftButton and self.esta_desenhando:
            self.esta_desenhando = False
            self.ponto_fim_desenho = event.position().toPoint()
            # 1. Descobre qual ferramenta está ligada agora

            if getattr(self, 'seta_ativada', False):
                ferramenta_atual = "seta"
            elif getattr(self, 'retangulo_ativado', False):
                ferramenta_atual = "retangulo"
            else:
                ferramenta_atual = "linha"
            
            # 2. Guarda a tupla com 3 informações: (Tipo, Ponto A, Ponto B)
            self.linhas_desenhadas.append((ferramenta_atual, self.ponto_inicio_desenho, self.ponto_fim_desenho))
            
            self.update()

    def ativar_modo_retangulo(self):
        # Desliga a seta se estiver ligada
        self.seta_ativada = False 
        
        # Inverte o estado do retângulo
        self.retangulo_ativado = not self.retangulo_ativado

        if self.retangulo_ativado:
            print("📦 Modo RETÂNGULO: LIGADO")
            self.setCursor(Qt.CrossCursor) 
        else:
            print("📦 Modo RETÂNGULO: DESLIGADO")
            self.setCursor(Qt.ArrowCursor)

    def ativar_modo_seta(self):
        self.seta_ativada = not self.seta_ativada

        if self.seta_ativada:
            print("🔧 Modo SETA: LIGADO")
            # Dica visual: mudar o cursor para uma cruzzinha ajuda muito na UX!
            self.setCursor(Qt.CrossCursor) 
        else:
            print("🔧 Modo SETA: DESLIGADO")
            # Volta o cursor ao normal
            self.setCursor(Qt.ArrowCursor)

    def acao_copiar(self):
        print("📋 Copiando imagem para a área de transferência...")
        
        if hasattr(self, 'painel'):
            self.painel.hide()
            # Força a tela a apagar o painel instantaneamente
            QApplication.processEvents()

        # 1. Congela a tela atual (sua foto + os desenhos vermelhos que você fez)
        print_final = self.grab(self.rect_imagem) 
        
        # 2. Joga para a memória do sistema
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(print_final)
        
        print("✅ Copiado! Fechando o editor...")
        
        self.limparPrintAntigo()

    def acao_salvar(self):
        print("💾 Preparando imagem para salvar...")
        
        # 1. Esconde o painel para não sair na foto
        if hasattr(self, 'painel'):
            self.painel.hide()
            QApplication.processEvents() 
        
        # 2. Recorta exatamente a área da imagem com as marcações
        print_final = self.grab(self.rect_imagem) 
        
        # 3. Sugere um nome de arquivo automático com a data/hora atual
        nome_sugerido = time.strftime("easyprint_%Y-%m-%d_%H-%M-%S.png")
        pasta_padrao = os.path.expanduser(f"~/Imagens/{nome_sugerido}")

        # 4. Abre a janela nativa do Linux
        # Retorna o caminho escolhido e o filtro de extensão
        caminho_arquivo, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Print", # Título da janela
            pasta_padrao,   # Onde a janela vai abrir por padrão
            "Imagens PNG (*.png);;Todos os Arquivos (*)" # Filtros
        )

        # 5. Verifica se o usuário confirmou o salvamento
        if caminho_arquivo:
            # O Qt cuida de converter e gravar os bytes no disco
            print_final.save(caminho_arquivo, "PNG")
            print(f"✅ Print salvo com sucesso em: {caminho_arquivo}")
            
            # Limpa e volta pro background
            self.limparPrintAntigo()
        else:
            print("❌ Salvamento cancelado pelo usuário.")
            # Se ele cancelou, traz o menu de volta pra ele não perder a edição!
            self.painel.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Configura o leitor de linha de comando
    parser = argparse.ArgumentParser(description="EasyPrint - Ferramenta de Captura")
    parser.add_argument('--trigger', action='store_true', help="Dispara o print no daemon que já está rodando")
    args = parser.parse_args()

    # Se rodou com "python main.py --trigger"
    if args.trigger:
        print("Buscando daemon do EasyPrint...")
        cliente = QLocalSocket()
        cliente.connectToServer("easyprint_socket")
        
        if cliente.waitForConnected(500):
            cliente.write(b"PRINT")
            cliente.waitForBytesWritten(500)
            print("✅ Comando enviado para o background!")
        else:
            print("❌ O EasyPrint não está rodando em background. Inicie-o primeiro.")
        sys.exit(0) # Morre imediatamente após dar a ordem

    # Se rodou normal (sem parâmetros), vira o Servidor de Fundo
    janela = EasyPrint()
    sys.exit(app.exec())