import React, { useEffect, useRef, useState } from "react";
const h = React.createElement;
export default function Voice({ onTranscript, disabled = false }) {
  const [listening, setListening] = useState(false),
    [speaking, setSpeaking] = useState(false),
    [error, setError] = useState("");
  const recognition = useRef(null),
    timer = useRef(null),
    transcript = useRef(onTranscript);
  transcript.current = onTranscript;
  const Recognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  useEffect(
    () => () => {
      if (recognition.current) {
        recognition.current.onresult = null;
        recognition.current.onend = null;
        recognition.current.onerror = null;
        recognition.current.abort();
      }
      clearTimeout(timer.current);
      window.speechSynthesis?.cancel();
    },
    [],
  );
  useEffect(() => {
    if (disabled) {
      recognition.current?.abort();
      setListening(false);
    }
  }, [disabled]);
  function record() {
    if (listening) {
      recognition.current?.stop();
      return;
    }
    if (!Recognition) return;
    setError("");
    const instance = new Recognition();
    recognition.current = instance;
    instance.lang = "vi-VN";
    instance.continuous = false;
    instance.interimResults = false;
    instance.onresult = (e) => {
      for (let i = e.resultIndex; i < e.results.length; i++)
        if (e.results[i].isFinal)
          transcript.current(e.results[i][0].transcript);
    };
    instance.onerror = (e) => {
      setError(
        e.error === "not-allowed"
          ? "Trình duyệt chưa cấp quyền microphone."
          : "Chưa nhận được giọng nói. Kiểm tra microphone, mạng và trình duyệt.",
      );
      setListening(false);
    };
    instance.onend = () => {
      setListening(false);
      clearTimeout(timer.current);
    };
    try {
      instance.start();
      setListening(true);
      timer.current = setTimeout(() => instance.stop(), 60000);
    } catch {
      setError("Không mở được microphone.");
    }
  }
  function speak() {
    const synth = window.speechSynthesis;
    if (!synth) return;
    synth.cancel();
    if (speaking) {
      setSpeaking(false);
      return;
    }
    const answer = [...document.querySelectorAll(".chat-message.assistant")].at(
      -1,
    );
    const text = [...(answer?.querySelectorAll(".ui-text") || [])]
      .map((n) => n.textContent)
      .join("\n");
    if (!text) {
      setError("Chưa có đoạn trả lời để đọc.");
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text.slice(0, 12000));
    utterance.lang = "vi-VN";
    const voice = synth.getVoices().find((v) => v.lang.startsWith("vi"));
    if (voice) utterance.voice = voice;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => {
      setSpeaking(false);
      setError("Thiết bị chưa đọc được văn bản.");
    };
    setSpeaking(true);
    synth.speak(utterance);
  }
  return h(
    "div",
    { className: "voice-controls" },
    h(
      "button",
      { type: "button", disabled: disabled || !Recognition, onClick: record },
      listening ? "Dừng nghe" : "Nhập bằng giọng nói",
    ),
    h(
      "button",
      {
        type: "button",
        disabled: disabled || !window.speechSynthesis,
        onClick: speak,
      },
      speaking ? "Dừng đọc" : "Đọc trả lời",
    ),
    h(
      "small",
      null,
      Recognition
        ? "Nhận giọng nói do trình duyệt xử lý, có thể gửi âm thanh tới dịch vụ của trình duyệt. Nội dung được đưa vào ô nhập để bạn kiểm tra trước khi gửi."
        : "Trình duyệt này chưa hỗ trợ nhận giọng nói.",
    ),
    error && h("p", { role: "status" }, error),
  );
}
