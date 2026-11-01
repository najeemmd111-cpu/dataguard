package dev.dataguard.explainer;

import java.util.ArrayList;
import java.util.List;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.metadata.ChatResponseMetadata;
import org.springframework.ai.chat.metadata.DefaultUsage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.model.Generation;
import org.springframework.ai.chat.prompt.Prompt;

/** Test double for a language model: returns a prepared answer and remembers the prompts it was sent. */
class FakeChatModel implements ChatModel {

    final List<Prompt> prompts = new ArrayList<>();
    private final String answer;
    private final RuntimeException failure;

    FakeChatModel(String answer) {
        this.answer = answer;
        this.failure = null;
    }

    FakeChatModel(RuntimeException failure) {
        this.answer = null;
        this.failure = failure;
    }

    @Override
    public ChatResponse call(Prompt prompt) {
        prompts.add(prompt);
        if (failure != null) {
            throw failure;
        }
        ChatResponseMetadata metadata = ChatResponseMetadata.builder().usage(new DefaultUsage(1200, 80)).build();
        return new ChatResponse(List.of(new Generation(new AssistantMessage(answer))), metadata);
    }
}
