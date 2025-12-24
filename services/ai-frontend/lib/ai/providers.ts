import {
  customProvider,
  extractReasoningMiddleware,
  wrapLanguageModel,
  type LanguageModelV3,
} from "ai";
import { isTestEnvironment } from "../constants";

// Dummy language model for cases where AI SDK tries to use models directly
// The actual AI processing is handled by agent-service via HTTP API
const createDummyModel = (modelName: string): LanguageModelV3 => {
  return {
    specificationVersion: 'V3',
    modelId: modelName,
    provider: 'agent-service',
    supportedUrls: {},

    async doGenerate() {
      console.warn(`[AI Provider] Model ${modelName} called directly - this should not happen. All AI requests should go through agent-service.`);
      throw new Error('AI models should be accessed through agent-service HTTP API, not directly through AI SDK');
    },

    async doStream() {
      console.warn(`[AI Provider] Model ${modelName} stream called directly - this should not happen. All AI requests should go through agent-service.`);
      throw new Error('AI models should be accessed through agent-service HTTP API, not directly through AI SDK');
    },
  } as LanguageModelV3;
};

export const myProvider = isTestEnvironment
  ? (() => {
      const {
        artifactModel,
        chatModel,
        reasoningModel,
        titleModel,
      } = require("./models.mock");
      return customProvider({
        languageModels: {
          "chat-model": chatModel,
          "chat-model-reasoning": reasoningModel,
          "title-model": titleModel,
          "artifact-model": artifactModel,
        },
      });
    })()
  : customProvider({
      languageModels: {
        "chat-model": createDummyModel("chat-model"),
        "chat-model-reasoning": wrapLanguageModel({
          model: createDummyModel("chat-model-reasoning"),
          middleware: extractReasoningMiddleware({ tagName: "think" }),
        }),
        "title-model": createDummyModel("title-model"),
        "artifact-model": createDummyModel("artifact-model"),
      },
    });
