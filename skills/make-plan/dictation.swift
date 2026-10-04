import AVFoundation
import Foundation
import Speech

let streamFlag = "--stream"
let streamSampleRate = 16000.0

func fail(_ message: String, _ code: Int32) -> Never {
    FileHandle.standardError.write("\(message)\n".data(using: .utf8)!)
    exit(code)
}

func emit(_ event: [String: String]) {
    guard let data = try? JSONSerialization.data(withJSONObject: event) else { return }
    FileHandle.standardOutput.write(data + Data([0x0A]))
}

func makeRecognizer() -> SFSpeechRecognizer {
    guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "ru-RU")), recognizer.isAvailable else {
        fail("recognizer unavailable", 3)
    }
    return recognizer
}

func transcribeFile(_ path: String) {
    let recognizer = makeRecognizer()
    let request = SFSpeechURLRecognitionRequest(url: URL(fileURLWithPath: path))
    request.requiresOnDeviceRecognition = recognizer.supportsOnDeviceRecognition
    request.shouldReportPartialResults = false
    request.addsPunctuation = true
    recognizer.recognitionTask(with: request) { result, error in
        if let error = error { fail(error.localizedDescription, 5) }
        guard let result = result, result.isFinal else { return }
        print(result.bestTranscription.formattedString)
        exit(0)
    }
}

/// Reads 16 kHz mono little-endian Int16 PCM from stdin until EOF and writes one JSON line per
/// recognition update to stdout: {"pid"}, then {"partial"}…, then {"final"} or {"error"}.
func transcribeStream() {
    let recognizer = makeRecognizer()
    let request = SFSpeechAudioBufferRecognitionRequest()
    request.requiresOnDeviceRecognition = recognizer.supportsOnDeviceRecognition
    request.shouldReportPartialResults = true
    request.addsPunctuation = true
    guard let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: streamSampleRate, channels: 1, interleaved: false) else {
        fail("audio format unavailable", 6)
    }
    emit(["pid": String(getpid())])
    var committed = ""
    recognizer.recognitionTask(with: request) { result, error in
        if let result = result {
            // After a pause Speech closes the utterance (metadata set) and restarts from an empty transcript.
            let text = [committed, result.bestTranscription.formattedString].filter { !$0.isEmpty }.joined(separator: " ")
            emit([result.isFinal ? "final" : "partial": text])
            if result.isFinal { exit(0) }
            if result.speechRecognitionMetadata != nil { committed = text }
        }
        if let error = error {
            emit(["error": error.localizedDescription])
            exit(5)
        }
    }
    DispatchQueue.global(qos: .userInitiated).async {
        var leftover = Data()
        while true {
            let chunk = FileHandle.standardInput.availableData
            if chunk.isEmpty { break }
            leftover.append(chunk)
            let usable = leftover.count - leftover.count % 2
            guard usable > 0, let buffer = pcmBuffer(leftover.prefix(usable), format: format) else { continue }
            leftover.removeFirst(usable)
            request.append(buffer)
        }
        request.endAudio()
    }
}

func pcmBuffer(_ bytes: Data, format: AVAudioFormat) -> AVAudioPCMBuffer? {
    let frames = bytes.count / 2
    guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frames)),
          let channel = buffer.floatChannelData?[0] else { return nil }
    bytes.withUnsafeBytes { raw in
        let samples = raw.bindMemory(to: Int16.self)
        for index in 0..<frames {
            channel[index] = Float(Int16(littleEndian: samples[index])) / Float(Int16.max)
        }
    }
    buffer.frameLength = AVAudioFrameCount(frames)
    return buffer
}

let argument = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ""
SFSpeechRecognizer.requestAuthorization { status in
    guard status == .authorized else { fail("not authorized", 4) }
    if argument == streamFlag {
        transcribeStream()
    } else {
        transcribeFile(argument)
    }
}
// Speech delivers its callbacks on the main queue; blocking the main thread deadlocks.
dispatchMain()
