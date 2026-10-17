import { expect, it, vi } from "vitest";
import { referenceNavigation } from "../media/inspector-navigation.js";

const click = (timeStamp, values = {}) => ({
  detail: 1,
  clientX: 100,
  clientY: 200,
  timeStamp,
  preventDefault: vi.fn(),
  ...values,
});

it("opens the first base immediately and ignores a second click on a redrawn ancestor link", () => {
  const post = vi.fn(),
    navigate = referenceNavigation(post);
  navigate(click(1000), "related", "middle");
  expect(post).toHaveBeenCalledExactlyOnceWith("related", { id: "middle" });
  const replacement = click(1080);
  navigate(replacement, "related", "root");
  expect(replacement.preventDefault).toHaveBeenCalledOnce();
  expect(post).toHaveBeenCalledTimes(1);
});

it("ignores the second click when the original base link survives the redraw", () => {
  const post = vi.fn(),
    navigate = referenceNavigation(post);
  navigate(click(1000), "related", "base");
  navigate(click(1080, { detail: 2 }), "related", "base");
  expect(post).toHaveBeenCalledTimes(1);
});

it("keeps distinct pointer choices and later clicks at the same position usable", () => {
  const post = vi.fn(),
    navigate = referenceNavigation(post);
  navigate(click(1000), "related", "first");
  navigate(click(1080, { clientY: 220 }), "related", "second");
  navigate(click(1800, { clientY: 220 }), "related", "third");
  expect(post.mock.calls).toEqual([
    ["related", { id: "first" }],
    ["related", { id: "second" }],
    ["related", { id: "third" }],
  ]);
});

it("allows repeated keyboard activation and protects member links with the same gesture", () => {
  const post = vi.fn(),
    navigate = referenceNavigation(post);
  navigate(click(1000), "properties", "method");
  navigate(click(1080), "related", "new-base");
  navigate(click(1090, { detail: 0 }), "related", "base");
  navigate(click(1100, { detail: 0 }), "related", "root");
  expect(post.mock.calls).toEqual([
    ["properties", { id: "method" }],
    ["related", { id: "base" }],
    ["related", { id: "root" }],
  ]);
});
