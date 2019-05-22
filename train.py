#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import time

import tensorflow as tf
import util

if __name__ == "__main__":
  config = util.initialize_from_env()

  report_frequency = config["report_frequency"]
  eval_frequency = config["eval_frequency"]
  max_step = config["max_step"]

  model = util.get_model(config)
  saver = tf.train.Saver()

  log_dir = config["log_dir"]
  writer = tf.summary.FileWriter(log_dir, flush_secs=20)

  max_r = 0
  best_step = 0
  with tf.Session() as session:
    session.run(tf.global_variables_initializer())
    model.start_enqueue_thread(session)
    accumulated_loss = 0.0

    ckpt = tf.train.get_checkpoint_state(log_dir)
    if ckpt and ckpt.model_checkpoint_path:
      print("Restoring from: {}".format(ckpt.model_checkpoint_path))
      saver.restore(session, ckpt.model_checkpoint_path)

    initial_time = time.time()
    while True:
      tf_loss, tf_global_step, _ = session.run([model.loss, model.global_step, model.train_op])
      accumulated_loss += tf_loss

      if tf_global_step % report_frequency == 0:
        total_time = time.time() - initial_time
        steps_per_second = tf_global_step / total_time

        average_loss = accumulated_loss / report_frequency
        print("[{}] loss={:.2f}, steps/s={:.2f}".format(tf_global_step, average_loss, steps_per_second))
        writer.add_summary(util.make_summary({"loss": average_loss}), tf_global_step)
        accumulated_loss = 0.0

      if tf_global_step % eval_frequency == 0:
        saver.save(session, os.path.join(log_dir, "model.ckpt"), global_step=tf_global_step)
        eval_summary, eval_r = model.evaluate(session)

        if eval_r > max_r:
          max_r = eval_r
          best_step = tf_global_step
          util.copy_checkpoint(os.path.join(log_dir, "model.ckpt-{}".format(tf_global_step)), os.path.join(log_dir, "model.max.ckpt"))

        writer.add_summary(eval_summary, tf_global_step)
        writer.add_summary(util.make_summary({"max_eval_f1": max_r}), tf_global_step)

        print("[{}] evaL_r={:.2f}, max_r={:.2f} at step {}".format(tf_global_step, eval_r*100, max_r*100, best_step))

      if max_step > 0 and tf_global_step >= max_step:
        break
