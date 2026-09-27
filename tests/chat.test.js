test("Jest is working", () => {
  expect(2 + 2).toBe(4);
});


// A simple chatbot function
function getAnswer(question) {
    if (question === "What is ReDI?") {
        return "ReDI School offers free digital education.";
    }

    return "Sorry, I don't have information about that.";
}


// Happy path: The chatbot knows the answer
test("returns an answer for a known question", () => {
    const result = getAnswer("What is ReDI?");

    expect(result).toBe(
        "ReDI School offers free digital education."
    );
});


// Unhappy path: The chatbot doesn't know the answer
test("returns a fallback for an unknown question", () => {
    const result = getAnswer("What is the weather today?");

    expect(result).toBe(
        "Sorry, I don't have information about that."
    );
});
