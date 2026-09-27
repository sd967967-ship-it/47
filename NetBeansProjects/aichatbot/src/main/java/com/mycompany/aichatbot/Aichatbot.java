/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.aichatbot;

/**
 *
 * @author sd967
 */

import org.vosk.LibVosk;
import org.vosk.LogLevel;
import org.vosk.Model;
import org.vosk.Recognizer;

import javax.sound.sampled.*;
import java.io.IOException;

public class Aichatbot {

   private static final String MODEL_PATH = "D:\\vosk-model-small-en-us-0.15";
    
    private static final float SAMPLE_RATE = 16000.0f;

    

    public static void main(String[] args) {

        System.out.println("================================");
        System.out.println("       Java Speech To Text");
        System.out.println("================================");

        // Disable unnecessary Vosk logging.
        LibVosk.setLogLevel(LogLevel.WARNINGS);

        try {
            runSpeechRecognition();
        } catch (Exception e) {
            System.err.println("Speech recognition failed:");
            e.printStackTrace();
        }
    }

    private static void runSpeechRecognition()
            throws IOException, LineUnavailableException {

        // Load speech recognition model.
        System.out.println("Loading speech model...");

        try (Model model = new Model(MODEL_PATH)) {

            System.out.println("Model loaded successfully.");
            System.out.println();

            // Configure microphone.
            AudioFormat format = new AudioFormat(
                    AudioFormat.Encoding.PCM_SIGNED,
                    SAMPLE_RATE,
                    16,
                    1,
                    2,
                    SAMPLE_RATE,
                    false
            );

            DataLine.Info info =
                    new DataLine.Info(TargetDataLine.class, format);

            if (!AudioSystem.isLineSupported(info)) {
                throw new LineUnavailableException(
                        "Microphone/audio format is not supported."
                );
            }

            TargetDataLine microphone =
                    (TargetDataLine) AudioSystem.getLine(info);

            microphone.open(format);

            // Create recognizer.
            try (Recognizer recognizer =
                         new Recognizer(model, SAMPLE_RATE)) {

                microphone.start();

                System.out.println("--------------------------------");
                System.out.println("Microphone started.");
                System.out.println("Start speaking...");
                System.out.println("Press ENTER to stop.");
                System.out.println("--------------------------------");

                // Thread responsible for stopping recognition.
                Thread stopThread = new Thread(() -> {
                    try {
                        System.in.read();
                    } catch (IOException e) {
                        e.printStackTrace();
                    }

                    microphone.stop();
                });

                stopThread.start();

                // Buffer for microphone data.
                byte[] buffer = new byte[4096];

                while (microphone.isOpen() &&
                       microphone.isActive()) {

                    int bytesRead =
                            microphone.read(
                                    buffer,
                                    0,
                                    buffer.length
                            );

                    if (bytesRead <= 0) {
                        continue;
                    }

                    // Send microphone data to Vosk.
                    if (recognizer.acceptWaveForm(
                            buffer,
                            bytesRead)) {

                        String result =
                                recognizer.getResult();

                        String text =
                                extractText(result);

                        if (!text.isBlank()) {
                            System.out.println(
                                    "Recognized: " + text
                            );
                        }

                    } else {

                        // Partial result while speaking.
                        String partial =
                                extractPartialResult(
                                        recognizer.getPartialResult()
                                );

                        if (!partial.isBlank()) {
                            System.out.print(
                                    "\rListening: " + partial + "    "
                            );
                        }
                    }
                }

                // Get final result.
                String finalResult =
                        recognizer.getFinalResult();

                String finalText =
                        extractText(finalResult);

                if (!finalText.isBlank()) {
                    System.out.println();
                    System.out.println(
                            "Final: " + finalText
                    );
                }

                microphone.close();

                System.out.println();
                System.out.println("Speech recognition stopped.");
            }
        }
    }

    private static String extractText(String json) {

        // Vosk returns JSON such as:
        // {"text" : "hello world"}

        int start = json.indexOf("\"text\"");
        if (start == -1) {
            return "";
        }

        start = json.indexOf(':', start);

        if (start == -1) {
            return "";
        }

        start++;

        int end = json.indexOf('}', start);

        if (end == -1) {
            return "";
        }

        String text =
                json.substring(start, end)
                    .replace("\"", "")
                    .trim();

        return text;
    }

    private static String extractPartialResult(String json) {

        // Vosk returns:
        // {"partial" : "hello wor"}

        int start = json.indexOf("\"partial\"");
        if (start == -1) {
            return "";
        }

        start = json.indexOf(':', start);

        if (start == -1) {
            return "";
        }

        start++;

        int end = json.indexOf('}', start);

        if (end == -1) {
            return "";
        }

        return json.substring(start, end)
                .replace("\"", "")
                .trim();
    }
}
