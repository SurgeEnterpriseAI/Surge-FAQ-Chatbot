import { render, screen } from "@testing-library/react";

import { MessageBubble } from "../components/chat/MessageBubble";
import type { ChatMessage } from "../hooks/useChatStream";

describe("MessageBubble", () => {
  it("renders markdown with a highlighted code block", () => {
    const message: ChatMessage = {
      id: "m1",
      role: "assistant",
      content: "Here is **bold** text.\n\n```python\nprint('hello')\n```",
    };

    render(<MessageBubble message={message} />);

    expect(screen.getByText("bold")).toBeInTheDocument();
    const bubble = screen.getByTestId("message-bubble");
    expect(bubble.querySelector("strong")).not.toBeNull();
    expect(bubble.querySelector("pre code")).not.toBeNull();
  });
});
