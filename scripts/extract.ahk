; extract.ahk — macro AutoHotkey v2 para extracción de 18 tablas SAP B1
;
; Uso:
;   1. Abrir SAP B1 Client con el Generador de Consultas LISTO (con
;      cursor en el textarea de SQL — click ahí primero manualmente)
;   2. Ejecutar este .ahk (doble click)
;   3. Presionar F8 para arrancar (pausa en cualquier momento con F10)
;   4. No mover el mouse ni tocar teclado mientras corre
;
; Requisitos:
;   - AutoHotkey v2 (https://www.autohotkey.com/)
;   - Windows con SAP B1 Client abierto en primer plano
;   - Los .sql del folder sql_queries/ (relativo a este script)
;
; Nota sobre seguridad:
;   El macro es agnóstico al layout exacto — usa shortcuts de teclado
;   de Windows (Alt+A para menú Archivo) + clicks en coords relativas
;   a la ventana activa. Si falla por cambio de layout, ver comentarios.

#Requires AutoHotkey v2.0
#SingleInstance Force

; Directorio de SQL queries (relativo al script)
ScriptDir := A_ScriptDir
SqlDir := ScriptDir "\..\sql_queries"
OutDir := ScriptDir "\..\data\drop"
DateStamp := FormatTime(A_Now, "yyyyMMdd")

; Orden de ejecución — maestros primero, transaccionales al final
Tables := [
    "OITB", "OACT", "OCRD", "OITM", "ITM1",
    "OITW", "OBTN", "OBTQ",
    "ORDR", "RDR1", "OPOR", "POR1",
    "OJDT", "JDT1",
    "OINV", "INV1", "OPCH", "PCH1"
]

; Estado
Running := false

; Hotkeys
F8::StartExtraction()
F10::StopExtraction()

ShowStatus() {
    MsgBox("AHK extract listo.`n`nF8 = iniciar extracción`nF10 = pausar/detener`n`n" .
           "Antes de F8:`n" .
           "  1. SAP B1 Client abierto`n" .
           "  2. Generador de Consultas visible`n" .
           "  3. Cursor en el textarea SQL (click manual)`n" .
           "  4. Carpeta de destino: " OutDir, "Extract SAP — preparado", 0)
}

ShowStatus()

StartExtraction() {
    global Running, Tables, SqlDir, OutDir, DateStamp
    if Running {
        MsgBox("Ya está corriendo.", "Extract", 48)
        return
    }
    if !DirExist(OutDir) {
        DirCreate(OutDir)
    }
    Running := true
    results := []

    Loop Tables.Length {
        if !Running {
            break
        }
        tbl := Tables[A_Index]
        sqlFile := SqlDir "\" tbl ".sql"
        if !FileExist(sqlFile) {
            results.Push(tbl " — NO sql file")
            continue
        }
        sqlText := FileRead(sqlFile, "UTF-8")
        outFile := OutDir "\" tbl "_" DateStamp ".xlsx"

        ; --- 1. Focus en SAP B1 (asumimos que está en primer plano)
        WinActivate("SAP Business One")
        Sleep 500

        ; --- 2. Limpiar textarea (Ctrl+A, Delete)
        Send "^a"
        Sleep 100
        Send "{Delete}"
        Sleep 100

        ; --- 3. Poner el SQL en clipboard y pegarlo (más rápido que SendText)
        A_Clipboard := sqlText
        Sleep 200
        Send "^v"
        Sleep 300

        ; --- 4. Ejecutar (F5)
        Send "{F5}"
        ; Esperar a que termine — tablas grandes pueden tardar 1-3 min
        ; El usuario puede tocar F8 para continuar al siguiente paso
        Sleep 5000

        ; --- 5. Archivo → Exportar → MS Excel vía menú
        ; Alt+A abre Archivo (la A está subrayada en SAP B1 español)
        Send "!a"
        Sleep 400
        ; bajar hasta "Exportar" con flechas
        Loop 9 {
            Send "{Down}"
            Sleep 60
        }
        ; abrir submenu
        Send "{Right}"
        Sleep 400
        ; bajar hasta "MS Excel" (típicamente 5 abajo)
        Loop 5 {
            Send "{Down}"
            Sleep 60
        }
        Send "{Enter}"
        Sleep 1500

        ; --- 6. Diálogo "Guardar como" — pegar path completo
        A_Clipboard := outFile
        Sleep 200
        Send "^a"
        Sleep 100
        Send "^v"
        Sleep 200
        Send "{Enter}"
        Sleep 2000

        ; --- 7. Cerrar ventana de resultados (Ctrl+W o Esc)
        Send "{Escape}"
        Sleep 300

        results.Push(tbl " — OK")
    }

    Running := false
    summary := ""
    for r in results {
        summary .= r "`n"
    }
    MsgBox(summary, "Extract terminado", 64)
}

StopExtraction() {
    global Running
    Running := false
    MsgBox("Detenido. Presiona F8 para retomar (empieza desde la primera tabla).", "Extract", 48)
}
