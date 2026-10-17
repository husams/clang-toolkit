export function referenceNavigation(post) {
  let lastPointer;
  return (event, type, id) => {
    if (event.detail > 0) {
      // Properties can redraw between the two clicks. The replacement link
      // may restart detail at 1, so also recognize the same physical gesture.
      const repeated =
        lastPointer &&
        event.timeStamp >= lastPointer.time &&
        event.timeStamp - lastPointer.time < 600 &&
        Math.hypot(
          event.clientX - lastPointer.x,
          event.clientY - lastPointer.y,
        ) <= 6;
      if (event.detail > 1 || repeated) {
        event.preventDefault();
        return;
      }
      lastPointer = {
        time: event.timeStamp,
        x: event.clientX,
        y: event.clientY,
      };
    } else lastPointer = undefined;
    post(type, { id });
  };
}
